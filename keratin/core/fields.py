from django.db import models, transaction
from django.db.models.signals import post_delete
from django_prose_editor.fields import ProseEditorField

from .images import to_webp
from .richtext import RICH_TEXT_EXTENSIONS, clean_rich_text


class RichTextField(ProseEditorField):
    """Текст из визуального редактора, очищенный и нормализованный."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("extensions", RICH_TEXT_EXTENSIONS)
        kwargs.setdefault("sanitize", clean_rich_text)
        super().__init__(*args, **kwargs)


class FileCleanupMixin:
    """Удаляет старый файл с диска, когда его заменили или очистили,
    и файл записи, когда удалили саму запись.

    Удаление выполняется после фиксации транзакции: при откате файл
    останется на месте вместе со ссылкой на него.
    """

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        if not cls._meta.abstract:
            post_delete.connect(self._delete_file, sender=cls, weak=False)

    def pre_save(self, model_instance, add):
        old_name = self._stored_name(model_instance)
        file = super().pre_save(model_instance, add)
        if old_name and old_name != file.name:
            self._delete_on_commit(old_name)
        return file

    def _stored_name(self, instance):
        if instance.pk is None:
            return None
        return (
            type(instance)
            ._base_manager.filter(pk=instance.pk)
            .values_list(self.attname, flat=True)
            .first()
        )

    def _delete_on_commit(self, name):
        transaction.on_commit(lambda: self.storage.delete(name))

    def _delete_file(self, sender, instance, **kwargs):
        file = getattr(instance, self.attname)
        if file:
            self._delete_on_commit(file.name)


class OwnedFileField(FileCleanupMixin, models.FileField):
    """Файл, который живёт ровно столько, сколько ссылающаяся на него
    запись."""


class WebPImageField(FileCleanupMixin, models.ImageField):
    """Фото, которое при сохранении перекодируется в WebP."""

    def __init__(self, *args, max_side=1600, **kwargs):
        self.max_side = max_side
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.max_side != 1600:
            kwargs["max_side"] = self.max_side
        return name, path, args, kwargs

    def pre_save(self, model_instance, add):
        file = getattr(model_instance, self.attname)
        if file and not file._committed:
            converted = to_webp(file, self.max_side)
            file.save(converted.name, converted, save=False)
        return super().pre_save(model_instance, add)
