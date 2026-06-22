from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        count = 0
        details = {}
        for obj in self:
            deleted_count, deleted_details = obj.delete()
            count += deleted_count
            for label, label_count in deleted_details.items():
                details[label] = details.get(label, 0) + label_count
        return count, details

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def _soft_delete_related(self):
        count = 0
        details = {}
        for relation in self._meta.related_objects:
            if relation.on_delete is not models.CASCADE:
                continue
            related_model = relation.related_model
            if not hasattr(related_model, 'is_deleted'):
                continue
            accessor = relation.get_accessor_name()
            if not accessor:
                continue
            try:
                related = getattr(self, accessor)
            except related_model.DoesNotExist:
                continue
            related_items = related.all() if hasattr(related, 'all') else [related]
            for item in related_items:
                deleted_count, deleted_details = item.delete()
                count += deleted_count
                for label, label_count in deleted_details.items():
                    details[label] = details.get(label, 0) + label_count
        return count, details

    def delete(self, using=None, keep_parents=False):
        count, details = self._soft_delete_related()
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])
        label = f'{self._meta.app_label}.{self.__class__.__name__}'
        details[label] = details.get(label, 0) + 1
        return count + 1, details

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])
