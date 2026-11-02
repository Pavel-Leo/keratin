from django.core.files.storage import FileSystemStorage, storages


class PrivateStorage(FileSystemStorage):
    """Хранилище файлов, которые не раздаются по ссылке.

    Каталог лежит вне MEDIA_ROOT, веб-сервер его не видит. Сюда попадают
    исходники роликов до перекодирования.
    """

    def url(self, name):
        raise ValueError("Файлы закрытого хранилища не отдаются по ссылке.")


def private_storage():
    return storages["private"]
