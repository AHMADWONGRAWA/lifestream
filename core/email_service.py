"""
core/email_service.py
Centralised email notification service for LifeStream.
Every notification trigger lives here — views just call these functions.
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def _send(subject, message, recipient_list, html_message=None):
    """
    Safe wrapper around Django's send_mail.
    Never crashes the view if email fails — logs the error instead.
    """
    try:
        if not recipient_list:
            return
        # Filter out empty emails
        recipients = [e for e in recipient_list if e and '@' in e]
        if not recipients:
            return

        if html_message:
            email = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipients,
            )
            email.attach_alternative(html_message, "text/html")
            email.send(fail_silently=False)
        else:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=False,
            )
        print(f"[EMAIL SENT] To: {recipients} | Subject: {subject}")
    except Exception as e:
        # Never crash the view — just log
        print(f"[EMAIL ERROR] {e} | Subject: {subject} | To: {recipient_list}")


# ─── 1. BLOOD REQUEST SUBMITTED ───────────────────────────────────────────────
def notify_request_submitted(blood_request):
    """
    Email to the patient confirming their request was received.
    """
    patient = blood_request.patient
    subject = f"[LifeStream] Blood Request Received — Ref: {blood_request.reference_no}"
    message = f"""Dear {patient.get_full_name() or patient.username},

Your blood request has been successfully submitted to LifeStream.

─────────────────────────────────
Request Details
─────────────────────────────────
Reference Number : {blood_request.reference_no}
Blood Type       : {blood_request.blood_type}
Quantity         : {blood_request.qty_units} unit(s)
Urgency          : {blood_request.get_urgency_display()}
Status           : {blood_request.get_status_display()}
Hospital         : {blood_request.hospital.name if blood_request.hospital else 'Searching nearest facility...'}
─────────────────────────────────

You can track your request at any time by visiting:
http://127.0.0.1:8000/request/track/?reference_no={blood_request.reference_no}

We are working to locate matching blood as quickly as possible.
If donors need to be alerted, they will be contacted immediately.

LifeStream — Every Drop Saves a Life
Islamic University Medical System
"""
    _send(subject, message, [patient.email])


# ─── 2. DONORS NOTIFIED ───────────────────────────────────────────────────────
def notify_donors_urgently(blood_request, donors):
    """
    Email each eligible donor about an urgent blood need.
    """
    for donor in donors:
        subject = f"[LifeStream] 🩸 Urgent Blood Need — {blood_request.blood_type}"
        message = f"""Dear {donor.get_full_name() or donor.username},

There is an urgent need for your blood type in your area.

─────────────────────────────────
Blood Need Details
─────────────────────────────────
Blood Type  : {blood_request.blood_type}
Quantity    : {blood_request.qty_units} unit(s)
Urgency     : {blood_request.get_urgency_display().upper()}
Reference   : {blood_request.reference_no}
─────────────────────────────────

If you are available to donate, please log in and respond to this alert:
http://127.0.0.1:8000/notifications/

Your response could save a life today. Every minute matters.

If you are unable to donate at this time, please update your availability 
in your profile so we can reach the right donors faster.

Thank you for being part of LifeStream.

LifeStream — Every Drop Saves a Life
Islamic University Medical System
"""
        _send(subject, message, [donor.email])


# ─── 3. REQUEST STATUS CHANGED ────────────────────────────────────────────────
def notify_status_change(blood_request):
    """
    Email the patient whenever their request status changes.
    """
    patient = blood_request.patient
    status_messages = {
        'matched':         'Great news! Blood matching your type has been located at a nearby facility.',
        'donor_committed': 'A donor has confirmed availability and is on their way to donate.',
        'fulfilled':       'Your blood request has been fulfilled. We hope for a speedy recovery.',
        'cancelled':       'Your blood request has been cancelled. Please contact us if this was an error.',
        'pending':         'Your request is still being processed. We are searching for matching donors.',
    }
    detail = status_messages.get(blood_request.status, 'Your request status has been updated.')

    subject = f"[LifeStream] Request Update — {blood_request.reference_no} is now '{blood_request.get_status_display()}'"
    message = f"""Dear {patient.get_full_name() or patient.username},

Your blood request status has been updated.

─────────────────────────────────
{blood_request.reference_no} — Status Update
─────────────────────────────────
Blood Type : {blood_request.blood_type}
New Status : {blood_request.get_status_display()}

{detail}
─────────────────────────────────

Track your request live:
http://127.0.0.1:8000/request/track/?reference_no={blood_request.reference_no}

LifeStream — Every Drop Saves a Life
Islamic University Medical System
"""
    _send(subject, message, [patient.email])


# ─── 4. DONOR RESPONDED ───────────────────────────────────────────────────────
def notify_donor_response(notification, response):
    """
    Email the hospital when a donor accepts or declines a request.
    """
    req      = notification.blood_request
    donor    = notification.donor
    hospital = req.hospital

    if not hospital or not hospital.contact_email:
        return

    if response == 'accepted':
        subject = f"[LifeStream] Donor Confirmed — {req.reference_no}"
        message = f"""A donor has confirmed availability for blood request {req.reference_no}.

─────────────────────────────────
Donor Information
─────────────────────────────────
Name       : {donor.get_full_name() or donor.username}
Blood Type : {donor.blood_type}
Phone      : {donor.phone or 'Not provided'}
City       : {donor.city or 'Not provided'}
─────────────────────────────────
Request    : {req.blood_type} × {req.qty_units} unit(s)
Urgency    : {req.get_urgency_display()}
─────────────────────────────────

Please contact the donor to coordinate the donation.

LifeStream — Every Drop Saves a Life
"""
        _send(subject, message, [hospital.contact_email])

    else:
        subject = f"[LifeStream] Donor Declined — {req.reference_no}"
        message = f"""A donor has declined the blood request {req.reference_no}.
The system will continue searching for available donors.

Blood Type : {req.blood_type}
Urgency    : {req.get_urgency_display()}

LifeStream — Every Drop Saves a Life
"""
        _send(subject, message, [hospital.contact_email])


# ─── 5. INVENTORY CRITICALLY LOW ─────────────────────────────────────────────
def notify_critical_inventory(inventory, admin_emails):
    """
    Email all admins when a blood type drops below the critical threshold.
    """
    subject = f"[LifeStream] ⚠ Critical Stock Alert — {inventory.blood_type} at {inventory.hospital.name}"
    message = f"""CRITICAL STOCK ALERT

Blood type {inventory.blood_type} at {inventory.hospital.name} has dropped to a critically low level.

─────────────────────────────────
Hospital   : {inventory.hospital.name}
City       : {inventory.hospital.city}
Blood Type : {inventory.blood_type}
Current    : {inventory.qty_available} unit(s) remaining
Threshold  : 5 units
─────────────────────────────────

Immediate action is required. Please arrange for restocking or 
broadcast a donor appeal for this blood type.

Manage inventory:
http://127.0.0.1:8000/inventory/

LifeStream — Every Drop Saves a Life
Islamic University Medical System
"""
    _send(subject, message, admin_emails)


# ─── 6. STAFF ACCOUNT CREATED BY ADMIN ───────────────────────────────────────
def notify_staff_account_created(staff_user, raw_password, hospital):
    """
    Email new hospital staff their login credentials after admin creates their account.
    """
    subject = "[LifeStream] Your Staff Account Has Been Created"
    message = f"""Dear {staff_user.get_full_name() or staff_user.username},

A LifeStream hospital staff account has been created for you by the system administrator.

─────────────────────────────────
Your Login Credentials
─────────────────────────────────
Portal URL : http://127.0.0.1:8000/login/
Username   : {staff_user.username}
Password   : {raw_password}
Hospital   : {hospital.name if hospital else 'Assigned by administrator'}
─────────────────────────────────

IMPORTANT: Please log in and change your password immediately from your profile page.

With your staff account you can:
  • View and update blood inventory at your facility
  • Manage incoming blood requests
  • Confirm blood availability for patients

If you did not expect this email or believe it was sent in error, 
please contact the system administrator immediately.

LifeStream — Every Drop Saves a Life
Islamic University Medical System
"""
    _send(subject, message, [staff_user.email])


# ─── 7. NEW BLOOD REQUEST TO HOSPITAL ────────────────────────────────────────
def notify_hospital_new_request(blood_request):
    """
    Email the matched hospital when a new blood request is assigned to them.
    """
    if not blood_request.hospital or not blood_request.hospital.contact_email:
        return
    subject = f"[LifeStream] New Blood Request — {blood_request.reference_no}"
    message = f"""A new blood request has been assigned to your facility.

─────────────────────────────────
Request Details
─────────────────────────────────
Reference  : {blood_request.reference_no}
Blood Type : {blood_request.blood_type}
Quantity   : {blood_request.qty_units} unit(s)
Urgency    : {blood_request.get_urgency_display()}
Patient    : {blood_request.patient.get_full_name() or blood_request.patient.username}
─────────────────────────────────

Please log in to confirm availability and update the request status:
http://127.0.0.1:8000/request/manage/

LifeStream — Every Drop Saves a Life
Islamic University Medical System
"""
    _send(subject, message, [blood_request.hospital.contact_email])
