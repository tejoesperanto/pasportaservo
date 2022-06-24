from django.apps import AppConfig
from django.db.models import signals
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class HostingConfig(AppConfig):
    name = "hosting"
    verbose_name = _("Hosting Service")

    def ready(self):
        # Models that should be watched and cause creation and deletion of the
        # related visibility object. The 2nd element of the tuple specifies the
        # field; the 3rd the specific visibility model.
        assets = [
            ('Profile', 'email', 'PublicEmail'),
            ('Phone', '', 'Phone'),
            ('Place', '', 'Place'),
            ('Place', 'family_members', 'FamilyMembers'),
        ]
        for model, field, asset_type in assets:
            make_visibility_receivers(
                'hosting.' + model,
                field + ('_' if field else '') + 'visibility',
                self.get_model('VisibilitySettingsFor' + asset_type)
            )
        signals.post_save.connect(profile_post_save, sender='hosting.Profile')


def make_visibility_receivers(for_sender, field_name, visibility_model):
    """
    Creates signal receivers for watched models. Must be defered because models
    do not become available until after the app is readied.
    - for_sender: the watched model.
    - field_name: the visibility field within the model.
    - visibility_model: the specific model according to the type of data.
    """
    uid = '{}--{}'.format(for_sender, field_name)
    foreign_key = '{}_id'.format(field_name)

    @receiver(signals.pre_save, sender=for_sender, weak=False, dispatch_uid=uid)
    def hosting_model_pre_save(sender, **kwargs):
        """
        Creates a new specific visibility object directly in database,
        if one does not yet exist.
        """
        if kwargs['raw'] or getattr(kwargs['instance'], foreign_key) is not None:
            return
        setattr(kwargs['instance'], field_name, visibility_model.prep(kwargs['instance']))

    @receiver(signals.post_save, sender=for_sender, weak=False, dispatch_uid=uid)
    def hosting_model_post_save(sender, **kwargs):
        """
        Links the specific visibility object to the newly created model
        instance. If the instance already has linkage, nothing happens.
        """
        if kwargs['raw'] or kwargs['created'] is False:
            return
        instance = kwargs['instance']
        visibility_model.objects.filter(
            id=getattr(instance, foreign_key), model_id__isnull=True,
        ).update(model_id=instance.pk)

    @receiver(signals.post_delete, sender=for_sender, weak=False, dispatch_uid=uid)
    def hosting_model_post_delete(sender, **kwargs):
        """
        Deletes the visibility object linked to the watched model instance.
        """
        visibility_model.objects.filter(
            id=getattr(kwargs['instance'], foreign_key),
        ).delete()


def profile_post_save(sender, **kwargs):
    """
    Creates a new preferences object for the newly created profile, in database.
    """
    from .models import Preferences
    instance = kwargs['instance']
    if kwargs['raw']:
        return
    if instance.user_id and not Preferences.objects.filter(profile_id=instance.pk).exists():
        Preferences.objects.create(profile=instance)
