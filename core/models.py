from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

class User(AbstractUser):
    ROLE_CHOICES = [('donor','Donor'),('patient','Patient / Receiver'),('hospital_staff','Hospital Staff'),('admin','Administrator')]
    BLOOD_CHOICES = [('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-')]
    role          = models.CharField(max_length=20, choices=ROLE_CHOICES, default='donor')
    blood_type    = models.CharField(max_length=5, choices=BLOOD_CHOICES, blank=True, null=True)
    phone         = models.CharField(max_length=20, blank=True)
    city          = models.CharField(max_length=80, blank=True)
    is_available  = models.BooleanField(default=True)
    last_donation = models.DateField(blank=True, null=True)
    hospital      = models.ForeignKey('Hospital', on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_members')
    def __str__(self): return f"{self.get_full_name() or self.username} ({self.role})"
    def is_donor(self): return self.role == 'donor'
    def is_patient(self): return self.role == 'patient'
    def is_hospital_staff(self): return self.role == 'hospital_staff'
    def is_admin_user(self): return self.role == 'admin'

class Hospital(models.Model):
    name=models.CharField(max_length=150); city=models.CharField(max_length=80)
    address=models.TextField(blank=True); contact_email=models.EmailField(blank=True)
    phone=models.CharField(max_length=20,blank=True); is_active=models.BooleanField(default=True)
    registered_at=models.DateTimeField(auto_now_add=True)
    def __str__(self): return f"{self.name} — {self.city}"
    class Meta: ordering=['name']

class Inventory(models.Model):
    BLOOD_CHOICES=[('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-')]
    hospital=models.ForeignKey(Hospital,on_delete=models.CASCADE,related_name='inventory')
    blood_type=models.CharField(max_length=5,choices=BLOOD_CHOICES)
    qty_available=models.PositiveIntegerField(default=0)
    critically_low=models.BooleanField(default=False)
    last_updated=models.DateTimeField(auto_now=True)
    LOW_THRESHOLD=5
    def update_stock(self,qty):
        self.qty_available=qty; self.critically_low=(qty<self.LOW_THRESHOLD); self.save()
    def check_availability(self,needed): return self.qty_available>=needed
    def __str__(self): return f"{self.hospital.name}|{self.blood_type}:{self.qty_available}"
    class Meta: unique_together=('hospital','blood_type'); ordering=['hospital','blood_type']; verbose_name_plural='Inventories'

def make_ref(): return 'LS-'+str(uuid.uuid4())[:8].upper()

class BloodRequest(models.Model):
    URGENCY_CHOICES=[('routine','Routine'),('urgent','Urgent'),('critical','Critical')]
    STATUS_CHOICES=[('pending','Pending — Searching'),('matched','Matched — Blood Located'),('donor_committed','Donor Committed'),('fulfilled','Fulfilled'),('cancelled','Cancelled')]
    BLOOD_CHOICES=[('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-')]
    reference_no=models.CharField(max_length=20,unique=True,default=make_ref,editable=False)
    patient=models.ForeignKey(User,on_delete=models.CASCADE,related_name='blood_requests')
    blood_type=models.CharField(max_length=5,choices=BLOOD_CHOICES)
    qty_units=models.PositiveIntegerField(default=1)
    urgency=models.CharField(max_length=10,choices=URGENCY_CHOICES,default='urgent')
    status=models.CharField(max_length=20,choices=STATUS_CHOICES,default='pending')
    hospital=models.ForeignKey(Hospital,on_delete=models.SET_NULL,null=True,blank=True,related_name='requests')
    notes=models.TextField(blank=True)
    submitted_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    def update_status(self,new_status): self.status=new_status; self.save()
    def __str__(self): return f"{self.reference_no}|{self.blood_type}|{self.status}"
    class Meta: ordering=['-submitted_at']

class Notification(models.Model):
    CHANNEL_CHOICES=[('email','Email'),('sms','SMS')]
    STATUS_CHOICES=[('sent','Sent'),('read','Read'),('accepted','Accepted'),('declined','Declined')]
    donor=models.ForeignKey(User,on_delete=models.CASCADE,related_name='notifications')
    blood_request=models.ForeignKey(BloodRequest,on_delete=models.CASCADE,related_name='notifications')
    channel=models.CharField(max_length=10,choices=CHANNEL_CHOICES,default='email')
    status=models.CharField(max_length=10,choices=STATUS_CHOICES,default='sent')
    message=models.TextField(blank=True)
    sent_at=models.DateTimeField(auto_now_add=True)
    def mark_as_read(self):
        if self.status=='sent': self.status='read'; self.save()
    def log_response(self,response): self.status=response; self.save()
    def __str__(self): return f"Notif→{self.donor.username}|{self.blood_request.reference_no}|{self.status}"
    class Meta: ordering=['-sent_at']

class Donation(models.Model):
    BLOOD_CHOICES=[('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-')]
    donor=models.ForeignKey(User,on_delete=models.CASCADE,related_name='donations')
    hospital=models.ForeignKey(Hospital,on_delete=models.SET_NULL,null=True,blank=True)
    blood_type=models.CharField(max_length=5,choices=BLOOD_CHOICES)
    qty_ml=models.PositiveIntegerField(default=450)
    donated_at=models.DateField()
    notes=models.TextField(blank=True)
    def __str__(self): return f"{self.donor.username}|{self.blood_type}|{self.donated_at}"
    class Meta: ordering=['-donated_at']

class AuditLog(models.Model):
    actor=models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
    action=models.CharField(max_length=120); target=models.CharField(max_length=120,blank=True)
    logged_at=models.DateTimeField(auto_now_add=True); detail=models.TextField(blank=True)
    def __str__(self): return f"[{self.logged_at:%Y-%m-%d %H:%M}]{self.actor}→{self.action}"
    class Meta: ordering=['-logged_at']
