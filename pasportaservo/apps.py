from django.contrib.admin.apps import AdminConfig


class PasportaServoAdminConfig(AdminConfig):
    default_site = 'pasportaservo.admin.AdminSite'
