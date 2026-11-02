// Портфолио: фильтр фото и видео по услугам и галерея на весь экран.
(function ($) {
  'use strict';

  $.fancybox.defaults.hash = false;
  $.fancybox.defaults.lang = 'ru';
  $.fancybox.defaults.i18n.ru = {
    CLOSE: 'Закрыть',
    NEXT: 'Дальше',
    PREV: 'Назад',
    ERROR: 'Не удалось загрузить. Попробуйте позже.',
    PLAY_START: 'Слайд-шоу',
    PLAY_STOP: 'Пауза',
    FULL_SCREEN: 'На весь экран',
    THUMBS: 'Миниатюры',
    DOWNLOAD: 'Скачать',
    SHARE: 'Поделиться',
    ZOOM: 'Увеличить'
  };

  // Размеры файла задают пропорции, но не ограничивают размер плеера.
  $(document).on('beforeLoad.fb', function (event, instance, slide) {
    if (slide.type !== 'video') {
      return;
    }
    slide.opts.ratio = slide.opts.width && slide.opts.height
      ? slide.opts.width / slide.opts.height : 9 / 16;
    slide.opts.width = null;
    slide.opts.height = null;
  });

  $(document).on('afterLoad.fb', function (event, instance, slide) {
    if (slide.type !== 'video' || !slide.$content) {
      return;
    }
    var video = slide.$content.find('video')[0];
    if (!video) {
      return;
    }
    function fitVideo() {
      if (video.videoWidth && video.videoHeight) {
        slide.opts.ratio = video.videoWidth / video.videoHeight;
        instance.updateSlide(slide);
      }
    }
    $(video).on('loadedmetadata', fitVideo);
    fitVideo();
  });

  var buttons = document.querySelectorAll('.portfolio-filter__button');
  var cards = document.querySelectorAll('.photo-card, .video-card');

  // Скрытые фото не должны попадать в листание галереи.
  function applyFilter(service) {
    Array.prototype.forEach.call(cards, function (card) {
      var hidden = service !== '' && card.getAttribute('data-service') !== service;
      card.hidden = hidden;
      var group = card.classList.contains('video-card') ? 'video' : 'photos';
      card.querySelector('a').setAttribute('data-fancybox', hidden ? group + '-hidden' : group);
    });
  }

  Array.prototype.forEach.call(buttons, function (button) {
    button.addEventListener('click', function () {
      Array.prototype.forEach.call(buttons, function (other) {
        other.setAttribute('aria-pressed', String(other === button));
      });
      applyFilter(button.getAttribute('data-filter'));
    });
  });
})(jQuery);
