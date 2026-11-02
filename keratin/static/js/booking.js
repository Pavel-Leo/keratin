// Онлайн-запись BookNow: https://booknow.ru/
// Страница записи открывается во фрейме поверх сайта, скрипт сервиса
// не подключается. Сообщения от фрейма принимаются только с его домена.
// Без JavaScript кнопка открывает страницу записи в новой вкладке.
(function () {
  var modal = document.getElementById('booking-modal');
  if (!modal) {
    return;
  }
  var frame = modal.querySelector('iframe');
  var closeButton = modal.querySelector('.booking-modal__close');
  var origin = new URL(frame.dataset.src).origin;
  var lastFocus = null;
  var background = document.querySelectorAll('body > :not(#booking-modal):not(script)');

  // Те же параметры, что передаёт официальный виджет EasyWeek.
  function frameUrl() {
    var url = new URL(frame.dataset.src);
    url.searchParams.set('ref', 'embed_widget');
    url.searchParams.set('back_url', 'iframe');
    url.searchParams.set('referrer', window.location.href);
    new URLSearchParams(window.location.search).forEach(function (value, key) {
      if (key.indexOf('utm_') === 0) {
        url.searchParams.set(key, value);
      }
    });
    return url.toString();
  }

  function open() {
    if (!frame.src) {
      frame.src = frameUrl();
    }
    lastFocus = document.activeElement;
    modal.hidden = false;
    background.forEach(function (element) {
      element.inert = true;
    });
    document.body.classList.add('booking-open');
    closeButton.focus();
  }

  function close() {
    if (modal.hidden) {
      return;
    }
    modal.hidden = true;
    background.forEach(function (element) {
      element.inert = false;
    });
    document.body.classList.remove('booking-open');
    if (lastFocus) {
      lastFocus.focus();
    }
  }

  document.addEventListener('click', function (event) {
    if (!(event.target instanceof Element)) {
      return;
    }
    if (event.target.closest('[data-booking]')) {
      event.preventDefault();
      open();
    } else if (event.target.closest('[data-booking-close]')) {
      close();
    }
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      close();
    }
    if (!modal.hidden && event.key === 'Tab') {
      if (event.shiftKey && document.activeElement === closeButton) {
        event.preventDefault();
        frame.focus();
      } else if (!event.shiftKey && document.activeElement === frame) {
        event.preventDefault();
        closeButton.focus();
      }
    }
  });

  window.addEventListener('message', function (event) {
    if (event.origin !== origin || event.source !== frame.contentWindow) {
      return;
    }
    var data = event.data || {};
    if (data.type === 'close') {
      close();
    } else if (data.type === 'redirect' && /^https:\/\//.test(data.url)) {
      window.location.assign(data.url);
    }
  });
})();
