from django.apps import AppConfig
from django.db.models import signals
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class HostingConfig(AppConfig):
    name = "hosting"
    verbose_name = _("Hosting Service")

    def ready(self):
        assets = [
            ('Profile', 'email', 'PublicEmail'),
            ('Phone', '', 'Phone'),
            ('Place', '', 'Place'),
            ('Place', 'family_members', 'FamilyMembers'),
        ]
        for model, field, asset_type in assets:
            make_receivers(
                'hosting.' + model,
                field + ('_' if field else '') + 'visibility',
                self.get_model('VisibilitySettingsFor' + asset_type)
            )


def make_receivers(for_sender, field_name, visibility_model):
    uid = '{}--{}'.format(for_sender, field_name)
    foreign_key = '{}_id'.format(field_name)

    @receiver(signals.pre_save, sender=for_sender, weak=False, dispatch_uid=uid)
    def hosting_model_pre_save(sender, **kwargs):
        if kwargs['raw'] or getattr(kwargs['instance'], foreign_key) is not None:
            return
        setattr(kwargs['instance'], field_name, visibility_model._prep())

    @receiver(signals.post_save, sender=for_sender, weak=False, dispatch_uid=uid)
    def hosting_model_post_save(sender, **kwargs):
        if kwargs['raw']:
            return
        instance = kwargs['instance']
        visibility_model.objects.filter(
            id=getattr(instance, foreign_key), model_id__isnull=True,
        ).update(model_id=instance.pk)

    @receiver(signals.post_delete, sender=for_sender, weak=False, dispatch_uid=uid)
    def hosting_model_post_delete(sender, **kwargs):
        visibility_model.objects.filter(
            id=getattr(kwargs['instance'], foreign_key),
        ).delete()
