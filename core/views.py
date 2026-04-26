from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.db import IntegrityError
from functools import wraps
import secrets
import string

from .models import User, Hospital, Inventory, BloodRequest, Notification, Donation, AuditLog
from .forms import (RegisterForm, LoginForm, ProfileForm, BloodRequestForm,
                    InventoryUpdateForm, DonationRecordForm, HospitalForm,
                    TrackRequestForm, StaffCreationForm)
from .email_service import (
    notify_request_submitted, notify_donors_urgently, notify_status_change,
    notify_donor_response, notify_critical_inventory, notify_staff_account_created,
    notify_hospital_new_request,
)

# ── HELPERS ───────────────────────────────────────────────────────────────────
def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if request.user.role not in roles and not request.user.is_superuser:
                messages.error(request, "You do not have permission to access that page.")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator

def log_action(user, action, target="", detail=""):
    AuditLog.objects.create(actor=user, action=action, target=target, detail=detail)

def _admin_emails():
    return list(User.objects.filter(role="admin", is_active=True).exclude(email="").values_list("email", flat=True))

def _generate_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$"
    return ''.join(secrets.choice(chars) for _ in range(length))

# ── HOME ──────────────────────────────────────────────────────────────────────
def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    stats = {
        "donors":    User.objects.filter(role="donor").count(),
        "hospitals": Hospital.objects.filter(is_active=True).count(),
        "requests":  BloodRequest.objects.filter(status="fulfilled").count(),
    }
    return render(request, "core/home.html", {"stats": stats})

# ── AUTH ──────────────────────────────────────────────────────────────────────
def register_view(request):
    """Public registration — donors and patients only. Staff are created by admin."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            user = form.save(commit=False)
            user.is_active = True
            if User.objects.filter(email=user.email).exists():
                form.add_error("email", "An account with this email already exists.")
                return render(request, "core/register.html", {"form": form})
            user.save()
            login(request, user)
            messages.success(request, f"Welcome to LifeStream, {user.first_name}! Your account is ready.")
            log_action(user, "REGISTER", user.username)
            return redirect("dashboard")
        except IntegrityError:
            form.add_error("username", "This username is already taken. Please choose a different one.")
    return render(request, "core/register.html", {"form": form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"Welcome back, {user.first_name or user.username}!")
        return redirect("dashboard")
    return render(request, "core/login.html", {"form": form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out. Thank you for using LifeStream.")
    return redirect("home")

# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    user = request.user
    ctx = {"user": user}
    if user.role == "donor" or user.is_superuser:
        ctx["my_notifications"] = Notification.objects.filter(donor=user).select_related("blood_request")[:5]
        ctx["my_donations"]     = Donation.objects.filter(donor=user)[:5]
        ctx["pending_requests"] = BloodRequest.objects.filter(status__in=["pending","matched"]).count()
    if user.role == "patient":
        ctx["my_requests"] = BloodRequest.objects.filter(patient=user)[:8]
    if user.role == "hospital_staff" and user.hospital:
        ctx["hospital"]  = user.hospital
        ctx["inventory"] = Inventory.objects.filter(hospital=user.hospital)
        ctx["requests"]  = BloodRequest.objects.filter(hospital=user.hospital).exclude(status="cancelled")[:10]
        ctx["critical"]  = Inventory.objects.filter(hospital=user.hospital, critically_low=True)
    if user.role == "admin" or user.is_superuser:
        ctx["total_donors"]    = User.objects.filter(role="donor").count()
        ctx["total_patients"]  = User.objects.filter(role="patient").count()
        ctx["total_hospitals"] = Hospital.objects.filter(is_active=True).count()
        ctx["open_requests"]   = BloodRequest.objects.filter(status__in=["pending","matched","donor_committed"]).count()
        ctx["critical_inv"]    = Inventory.objects.filter(critically_low=True).count()
        ctx["recent_requests"] = BloodRequest.objects.all()[:8]
        ctx["recent_logs"]     = AuditLog.objects.all()[:6]
        ctx["blood_summary"]   = Inventory.objects.values("blood_type").annotate(total=Sum("qty_available")).order_by("blood_type")
    return render(request, "core/dashboard.html", ctx)

# ── PROFILE ───────────────────────────────────────────────────────────────────
@login_required
def profile_view(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("profile")
    return render(request, "core/profile.html", {"form": form})

# ── BLOOD REQUESTS ────────────────────────────────────────────────────────────
@login_required
@role_required("patient", "admin")
def submit_request(request):
    form = BloodRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        req = form.save(commit=False)
        req.patient = request.user
        req.save()

        # Check inventory availability
        inv = Inventory.objects.filter(
            blood_type=req.blood_type, qty_available__gte=req.qty_units
        ).first()

        if inv:
            req.status   = "matched"
            req.hospital = inv.hospital
            req.save()
            messages.success(request, f"Blood ({req.blood_type}) available at {inv.hospital.name}. Ref: {req.reference_no}")
            # Email hospital about new request
            notify_hospital_new_request(req)
        else:
            # Alert matching donors
            donors = User.objects.filter(
                role="donor", blood_type=req.blood_type,
                is_available=True, is_active=True
            )
            for donor in donors:
                msg = (f"Urgent: {req.blood_type} ({req.qty_units} unit(s)) needed. "
                       f"Urgency: {req.get_urgency_display()}. Ref: {req.reference_no}")
                Notification.objects.create(
                    donor=donor, blood_request=req, message=msg, channel="email"
                )
            # Send real emails to donors
            notify_donors_urgently(req, donors)
            messages.warning(request, f"No immediate stock found. {donors.count()} donor(s) have been alerted. Ref: {req.reference_no}")

        # Confirm email to patient
        notify_request_submitted(req)
        log_action(request.user, "SUBMIT_REQUEST", req.reference_no)
        return redirect("my_requests")
    return render(request, "core/submit_request.html", {"form": form})

@login_required
@role_required("patient", "admin")
def my_requests(request):
    reqs = BloodRequest.objects.filter(patient=request.user)
    return render(request, "core/my_requests.html", {"requests": reqs})

def track_request(request):
    form = TrackRequestForm(request.GET or None)
    result = None
    if form.is_valid():
        ref = form.cleaned_data["reference_no"].strip().upper()
        try:
            result = BloodRequest.objects.get(reference_no=ref)
        except BloodRequest.DoesNotExist:
            messages.error(request, f'No request found with reference "{ref}". Please check and try again.')
    return render(request, "core/track_request.html", {"form": form, "result": result})

@login_required
@role_required("hospital_staff", "admin")
def manage_requests(request):
    if request.user.role == "hospital_staff" and request.user.hospital:
        reqs = BloodRequest.objects.filter(hospital=request.user.hospital)
    else:
        reqs = BloodRequest.objects.all()
    status_filter = request.GET.get("status", "")
    if status_filter:
        reqs = reqs.filter(status=status_filter)
    return render(request, "core/manage_requests.html", {
        "requests": reqs,
        "status_filter": status_filter,
        "STATUS_CHOICES": BloodRequest.STATUS_CHOICES,
    })

@login_required
@role_required("hospital_staff", "admin")
def update_request_status(request, pk):
    req        = get_object_or_404(BloodRequest, pk=pk)
    new_status = request.POST.get("status")
    if new_status in dict(BloodRequest.STATUS_CHOICES):
        old_status = req.status
        req.update_status(new_status)
        log_action(request.user, "UPDATE_REQUEST_STATUS", req.reference_no, f"{old_status} → {new_status}")
        # Email patient about status change
        notify_status_change(req)
        messages.success(request, f'Request {req.reference_no} updated to "{req.get_status_display()}". Patient has been notified by email.')
    return redirect("manage_requests")

# ── INVENTORY ─────────────────────────────────────────────────────────────────
@login_required
@role_required("hospital_staff", "admin")
def inventory_view(request):
    if request.user.role == "hospital_staff" and request.user.hospital:
        hospital = request.user.hospital
        inv_list = Inventory.objects.filter(hospital=hospital)
    else:
        hospital = None
        inv_list = Inventory.objects.all().select_related("hospital")
    return render(request, "core/inventory.html", {"inventory": inv_list, "hospital": hospital})

@login_required
@role_required("hospital_staff", "admin")
def update_inventory(request, pk):
    inv  = get_object_or_404(Inventory, pk=pk)
    form = InventoryUpdateForm(request.POST or None, instance=inv)
    if request.method == "POST" and form.is_valid():
        old_qty = inv.qty_available
        new_qty = form.cleaned_data["qty_available"]
        inv.update_stock(new_qty)
        log_action(request.user, "UPDATE_INVENTORY", f"{inv.hospital.name}|{inv.blood_type}", f"{old_qty} → {new_qty}")
        if inv.critically_low:
            # Email all admins
            notify_critical_inventory(inv, _admin_emails())
            messages.warning(request, f"⚠ {inv.blood_type} at {inv.hospital.name} is critically low ({new_qty} units). Admins have been alerted.")
        else:
            messages.success(request, f"Inventory updated: {inv.blood_type} at {inv.hospital.name} = {new_qty} units.")
        return redirect("inventory")
    return render(request, "core/update_inventory.html", {"form": form, "inv": inv})

@login_required
@role_required("hospital_staff", "admin")
def add_inventory(request):
    form = InventoryUpdateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        inv          = form.save(commit=False)
        inv.hospital = request.user.hospital or Hospital.objects.first()
        inv.critically_low = inv.qty_available < Inventory.LOW_THRESHOLD
        inv.save()
        messages.success(request, f"Inventory record added for {inv.blood_type}.")
        return redirect("inventory")
    return render(request, "core/add_inventory.html", {"form": form})

# ── DONOR NOTIFICATIONS ───────────────────────────────────────────────────────
@login_required
def donor_notifications(request):
    notifs = Notification.objects.filter(donor=request.user).select_related("blood_request")
    for n in notifs:
        n.mark_as_read()
    return render(request, "core/donor_notifications.html", {"notifications": notifs})

@login_required
@role_required("donor")
def respond_notification(request, pk):
    notif    = get_object_or_404(Notification, pk=pk, donor=request.user)
    response = request.POST.get("response")
    if response in ("accepted", "declined"):
        notif.log_response(response)
        if response == "accepted":
            notif.blood_request.update_status("donor_committed")
            notify_donor_response(notif, "accepted")
            notify_status_change(notif.blood_request)
            messages.success(request, "Thank you! The hospital has been notified of your availability.")
            log_action(request.user, "DONOR_ACCEPTED", notif.blood_request.reference_no)
        else:
            notify_donor_response(notif, "declined")
            messages.info(request, "Your response has been recorded. Thank you.")
    return redirect("donor_notifications")

@login_required
@role_required("donor")
def donation_history(request):
    donations = Donation.objects.filter(donor=request.user)
    return render(request, "core/donation_history.html", {"donations": donations})

@login_required
@role_required("donor")
def add_donation(request):
    form = DonationRecordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d        = form.save(commit=False)
        d.donor  = request.user
        d.save()
        request.user.last_donation = d.donated_at
        request.user.save()
        messages.success(request, "Donation recorded. Thank you for saving lives!")
        log_action(request.user, "RECORD_DONATION", str(d.donated_at))
        return redirect("donation_history")
    return render(request, "core/add_donation.html", {"form": form})

# ── SEARCH ────────────────────────────────────────────────────────────────────
def search_blood(request):
    BLOOD_TYPES = ["A+","A-","B+","B-","AB+","AB-","O+","O-"]
    blood_type  = request.GET.get("blood_type", "")
    city        = request.GET.get("city", "")
    results     = []
    if blood_type or city:
        qs = Inventory.objects.filter(qty_available__gt=0).select_related("hospital")
        if blood_type: qs = qs.filter(blood_type=blood_type)
        if city:       qs = qs.filter(hospital__city__icontains=city)
        results = qs
    return render(request, "core/search_blood.html", {
        "results": results, "blood_type": blood_type,
        "city": city, "blood_types": BLOOD_TYPES,
    })

# ── ADMIN — USERS ─────────────────────────────────────────────────────────────
@login_required
@role_required("admin")
def admin_users(request):
    role_filter = request.GET.get("role", "")
    users = User.objects.filter(role=role_filter) if role_filter else User.objects.all().order_by("role", "username")
    return render(request, "core/admin_users.html", {
        "users": users, "role_filter": role_filter, "ROLES": User.ROLE_CHOICES,
    })

@login_required
@role_required("admin")
def toggle_user(request, pk):
    target           = get_object_or_404(User, pk=pk)
    target.is_active = not target.is_active
    target.save()
    log_action(request.user, "TOGGLE_USER", target.username)
    status = "activated" if target.is_active else "deactivated"
    messages.success(request, f"User {target.username} has been {status}.")
    return redirect("admin_users")

# ── ADMIN — CREATE STAFF (replaces public registration for hospital_staff) ────
@login_required
@role_required("admin")
def create_staff(request):
    """
    Only admins can create hospital staff accounts.
    A secure random password is generated and emailed to the new staff member.
    """
    form = StaffCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            staff = form.save(commit=False)
            staff.role      = "hospital_staff"
            staff.is_active = True

            # Check email uniqueness
            if User.objects.filter(email=staff.email).exists():
                form.add_error("email", "An account with this email already exists.")
                return render(request, "core/admin_create_staff.html", {"form": form})

            # Generate a secure random password
            raw_password = _generate_password()
            staff.set_password(raw_password)
            staff.save()

            # Email credentials to the new staff member
            hospital = staff.hospital
            notify_staff_account_created(staff, raw_password, hospital)

            log_action(request.user, "CREATE_STAFF", staff.username,
                       f"Hospital: {hospital.name if hospital else 'None'}")
            messages.success(
                request,
                f"Staff account for {staff.get_full_name() or staff.username} created successfully. "
                f"Login credentials have been sent to {staff.email}."
            )
            return redirect("admin_users")
        except IntegrityError:
            form.add_error("username", "This username is already taken.")

    return render(request, "core/admin_create_staff.html", {"form": form})

# ── ADMIN — HOSPITALS ─────────────────────────────────────────────────────────
@login_required
@role_required("admin")
def admin_hospitals(request):
    form      = HospitalForm(request.POST or None)
    hospitals = Hospital.objects.all()
    if request.method == "POST" and form.is_valid():
        h = form.save()
        for bt in ["A+","A-","B+","B-","AB+","AB-","O+","O-"]:
            Inventory.objects.get_or_create(hospital=h, blood_type=bt, defaults={"qty_available": 0})
        log_action(request.user, "ADD_HOSPITAL", h.name)
        messages.success(request, f'Hospital "{h.name}" registered successfully.')
        return redirect("admin_hospitals")
    return render(request, "core/admin_hospitals.html", {"form": form, "hospitals": hospitals})

# ── ADMIN — REPORTS ───────────────────────────────────────────────────────────
@login_required
@role_required("admin")
def reports_view(request):
    blood_types = ["A+","A-","B+","B-","AB+","AB-","O+","O-"]
    ctx = {
        "total_requests":   BloodRequest.objects.count(),
        "fulfilled":        BloodRequest.objects.filter(status="fulfilled").count(),
        "pending":          BloodRequest.objects.filter(status="pending").count(),
        "total_donors":     User.objects.filter(role="donor").count(),
        "available_donors": User.objects.filter(role="donor", is_available=True).count(),
        "total_donations":  Donation.objects.count(),
        "hospitals":        Hospital.objects.filter(is_active=True).count(),
        "critical_inv":     Inventory.objects.filter(critically_low=True),
        "blood_summary": [
            {
                "type":   bt,
                "total":  Inventory.objects.filter(blood_type=bt).aggregate(s=Sum("qty_available"))["s"] or 0,
                "donors": User.objects.filter(role="donor", blood_type=bt).count(),
            }
            for bt in blood_types
        ],
        "recent_activity": AuditLog.objects.all()[:10],
    }
    return render(request, "core/reports.html", ctx)
