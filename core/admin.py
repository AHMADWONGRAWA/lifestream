from django.contrib import admin
from .models import User, Hospital, Inventory, BloodRequest, Notification, Donation, AuditLog

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display=['username','first_name','role','blood_type','city','is_active']
    list_filter=['role','blood_type','is_active']
    search_fields=['username','first_name','email']

@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display=['name','city','phone','is_active']

@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display=['hospital','blood_type','qty_available','critically_low']

@admin.register(BloodRequest)
class BloodRequestAdmin(admin.ModelAdmin):
    list_display=['reference_no','patient','blood_type','urgency','status','submitted_at']
    list_filter=['status','urgency','blood_type']

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display=['donor','blood_request','status','sent_at']

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display=['donor','blood_type','qty_ml','donated_at']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display=['logged_at','actor','action','target']
    readonly_fields=['logged_at']
