"""
Management command: python manage.py seed
Creates all demo data for the LifeStream exhibition.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from core.models import User, Hospital, Inventory, BloodRequest, Notification, Donation


class Command(BaseCommand):
    help = 'Seed the database with demo data for the LifeStream exhibition'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Seeding LifeStream database...'))

        # ── HOSPITALS ──────────────────────────────────────────────────────────
        hospitals_data = [
            {'name': 'King Fahd Hospital',       'city': 'Jeddah',  'phone': '+966-12-667-0000', 'contact_email': 'info@kfh.sa'},
            {'name': 'King Abdullah Medical City','city': 'Makkah',  'phone': '+966-12-563-3333', 'contact_email': 'info@kamc.sa'},
            {'name': 'King Salman Hospital',      'city': 'Riyadh',  'phone': '+966-11-435-9999', 'contact_email': 'info@ksh.sa'},
            {'name': 'Prince Sultan Hospital',    'city': 'Medina',  'phone': '+966-14-823-0000', 'contact_email': 'info@psh.sa'},
            {'name': 'Islamic University Clinic', 'city': 'Medina',  'phone': '+966-14-846-0000', 'contact_email': 'clinic@iu.edu.sa'},
        ]
        hospitals = []
        for h in hospitals_data:
            obj, created = Hospital.objects.get_or_create(name=h['name'], defaults=h)
            hospitals.append(obj)
            if created:
                self.stdout.write(f'  ✔ Hospital: {obj.name}')

        # ── INVENTORY ──────────────────────────────────────────────────────────
        blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        import random
        random.seed(42)
        for hospital in hospitals:
            for bt in blood_types:
                qty = random.choice([0, 3, 8, 15, 25, 40, 55])
                Inventory.objects.get_or_create(
                    hospital=hospital, blood_type=bt,
                    defaults={'qty_available': qty, 'critically_low': qty < 5}
                )
        self.stdout.write(f'  ✔ Inventory records created')

        # ── ADMIN USER ─────────────────────────────────────────────────────────
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin', email='admin@lifestream.sa',
                password='admin123', first_name='System', last_name='Administrator',
                role='admin'
            )
            self.stdout.write(f'  ✔ Admin: admin / admin123')
        else:
            admin = User.objects.get(username='admin')

        # ── DONORS ─────────────────────────────────────────────────────────────
        donors_data = [
            {'username':'ahmed_donor',  'first_name':'Ahmed',   'last_name':'Al-Rashid',  'blood_type':'O+',  'city':'Jeddah',  'phone':'+966501111111'},
            {'username':'fatima_donor', 'first_name':'Fatima',  'last_name':'Al-Zahrani', 'blood_type':'A+',  'city':'Riyadh',  'phone':'+966502222222'},
            {'username':'omar_donor',   'first_name':'Omar',    'last_name':'Al-Ghamdi',  'blood_type':'B+',  'city':'Medina',  'phone':'+966503333333'},
            {'username':'sara_donor',   'first_name':'Sara',    'last_name':'Al-Harthi',  'blood_type':'AB+', 'city':'Makkah',  'phone':'+966504444444'},
            {'username':'khalid_donor', 'first_name':'Khalid',  'last_name':'Al-Otaibi',  'blood_type':'O-',  'city':'Jeddah',  'phone':'+966505555555'},
            {'username':'noura_donor',  'first_name':'Noura',   'last_name':'Al-Shehri',  'blood_type':'A-',  'city':'Riyadh',  'phone':'+966506666666'},
        ]
        donors = []
        for d in donors_data:
            if not User.objects.filter(username=d['username']).exists():
                u = User(**d, role='donor', is_available=True, email=f"{d['username']}@demo.sa")
                u.set_password('demo123')
                u.save()
                donors.append(u)
                self.stdout.write(f"  ✔ Donor: {d['username']} / demo123")
            else:
                donors.append(User.objects.get(username=d['username']))

        # ── PATIENTS ───────────────────────────────────────────────────────────
        patients_data = [
            {'username':'patient1', 'first_name':'Ali',     'last_name':'Hassan',   'blood_type':'A+',  'city':'Jeddah'},
            {'username':'patient2', 'first_name':'Maryam',  'last_name':'Ibrahim',  'blood_type':'O+',  'city':'Riyadh'},
            {'username':'patient3', 'first_name':'Tariq',   'last_name':'Al-Malik', 'blood_type':'B-',  'city':'Medina'},
        ]
        patients = []
        for p in patients_data:
            if not User.objects.filter(username=p['username']).exists():
                u = User(**p, role='patient', email=f"{p['username']}@demo.sa")
                u.set_password('demo123')
                u.save()
                patients.append(u)
                self.stdout.write(f"  ✔ Patient: {p['username']} / demo123")
            else:
                patients.append(User.objects.get(username=p['username']))

        # ── HOSPITAL STAFF ─────────────────────────────────────────────────────
        if not User.objects.filter(username='staff1').exists():
            staff = User(username='staff1', first_name='Rania', last_name='Al-Dosari',
                        role='hospital_staff', email='staff1@demo.sa',
                        hospital=hospitals[0], city='Jeddah')
            staff.set_password('demo123')
            staff.save()
            self.stdout.write(f'  ✔ Staff: staff1 / demo123 → {hospitals[0].name}')

        # ── BLOOD REQUESTS ─────────────────────────────────────────────────────
        requests_data = [
            {'patient': patients[0], 'blood_type': 'A+', 'qty_units': 2, 'urgency': 'urgent',   'status': 'matched',   'hospital': hospitals[0]},
            {'patient': patients[1], 'blood_type': 'O+', 'qty_units': 1, 'urgency': 'critical',  'status': 'pending',   'hospital': None},
            {'patient': patients[2], 'blood_type': 'B-', 'qty_units': 3, 'urgency': 'routine',   'status': 'fulfilled', 'hospital': hospitals[2]},
            {'patient': patients[0], 'blood_type': 'A+', 'qty_units': 1, 'urgency': 'urgent',    'status': 'donor_committed', 'hospital': hospitals[0]},
        ]
        for r in requests_data:
            if not BloodRequest.objects.filter(patient=r['patient'], blood_type=r['blood_type'], status=r['status']).exists():
                BloodRequest.objects.create(**r)
        self.stdout.write(f'  ✔ Blood requests created')

        # ── DONATIONS ──────────────────────────────────────────────────────────
        for i, donor in enumerate(donors[:3]):
            if not Donation.objects.filter(donor=donor).exists():
                Donation.objects.create(
                    donor=donor,
                    hospital=hospitals[i % len(hospitals)],
                    blood_type=donor.blood_type,
                    qty_ml=450,
                    donated_at=date.today() - timedelta(days=30 * (i + 1))
                )
        self.stdout.write(f'  ✔ Donation records created')

        # ── NOTIFICATIONS ──────────────────────────────────────────────────────
        pending_req = BloodRequest.objects.filter(status='pending').first()
        if pending_req:
            for donor in donors[:2]:
                if not Notification.objects.filter(donor=donor, blood_request=pending_req).exists():
                    Notification.objects.create(
                        donor=donor,
                        blood_request=pending_req,
                        message=f"Urgent: {pending_req.blood_type} blood needed. Ref: {pending_req.reference_no}",
                        channel='email',
                        status='sent'
                    )
        self.stdout.write(f'  ✔ Notifications created')

        self.stdout.write(self.style.SUCCESS('\n✅ Database seeded successfully!\n'))
        self.stdout.write('─' * 50)
        self.stdout.write('LOGIN CREDENTIALS:')
        self.stdout.write('  Admin:        admin    / admin123')
        self.stdout.write('  Donors:       ahmed_donor, fatima_donor, omar_donor / demo123')
        self.stdout.write('  Patients:     patient1, patient2, patient3 / demo123')
        self.stdout.write('  Hospital Staff: staff1 / demo123')
        self.stdout.write('─' * 50)
        self.stdout.write('Run:  python manage.py runserver')
        self.stdout.write('Open: http://127.0.0.1:8000')
