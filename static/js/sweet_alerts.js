(function () {
  function iconForTag(tag) {
    if (!tag) return 'info';
    if (tag.indexOf('danger') !== -1 || tag.indexOf('error') !== -1) return 'error';
    if (tag.indexOf('success') !== -1) return 'success';
    if (tag.indexOf('warning') !== -1) return 'warning';
    return 'info';
  }

  function titleForIcon(icon) {
    if (icon === 'success') return 'Success';
    if (icon === 'error') return 'Error';
    if (icon === 'warning') return 'Warning';
    return 'Notice';
  }

  function showMessage(message, tag) {
    if (!message) return Promise.resolve();

    if (!window.Swal) {
      window.alert(message);
      return Promise.resolve();
    }

    var icon = iconForTag(tag);
    return window.Swal.fire({
      icon: icon,
      title: titleForIcon(icon),
      text: message,
      confirmButtonText: 'OK',
      confirmButtonColor: '#5b5fef',
      background: '#111827',
      color: '#f8fafc',
      customClass: {
        popup: 'examly-swal-popup'
      }
    });
  }

  function extractConfirmMessage(value) {
    if (!value) return 'Are you sure you want to continue?';
    var match = value.match(/confirm\(\s*(['"])(.*?)\1\s*\)/);
    return match ? match[2] : 'Are you sure you want to continue?';
  }

  function showConfirm(message) {
    if (!window.Swal) {
      return Promise.resolve(window.confirm(message));
    }

    return window.Swal.fire({
      icon: 'warning',
      title: 'Are you sure?',
      text: message,
      showCancelButton: true,
      confirmButtonText: 'Yes, continue',
      cancelButtonText: 'Cancel',
      confirmButtonColor: '#ef4444',
      cancelButtonColor: '#64748b',
      background: '#111827',
      color: '#f8fafc',
      customClass: {
        popup: 'examly-swal-popup'
      }
    }).then(function (result) {
      return result.isConfirmed;
    });
  }

  window.examlyShowAlert = showMessage;
  window.examlyShowConfirm = showConfirm;

  document.addEventListener('DOMContentLoaded', function () {
    var messages = window.examlyMessages || [];
    var chain = Promise.resolve();
    messages.forEach(function (item) {
      chain = chain.then(function () {
        return showMessage(item.message, item.tags);
      });
    });

    if (window.Swal && !window.__examlyNativeAlertPatched) {
      window.__examlyNativeAlertPatched = true;
      window.alert = function (message) {
        showMessage(String(message || ''), 'info');
      };
    }

    document.addEventListener('click', function (event) {
      var link = event.target.closest('a[onclick]');
      if (!link || link.dataset.examlyConfirmBypass === '1') return;
      var handler = link.getAttribute('onclick') || '';
      if (handler.indexOf('confirm(') === -1) return;

      event.preventDefault();
      event.stopImmediatePropagation();

      showConfirm(extractConfirmMessage(handler)).then(function (confirmed) {
        if (!confirmed) return;
        link.dataset.examlyConfirmBypass = '1';
        if (link.href) {
          window.location.href = link.href;
        } else {
          link.click();
        }
      });
    }, true);

    document.addEventListener('submit', function (event) {
      var form = event.target;
      if (!form || !form.matches || !form.matches('form[onsubmit]') || form.dataset.examlyConfirmBypass === '1') return;
      var handler = form.getAttribute('onsubmit') || '';
      if (handler.indexOf('confirm(') === -1) return;

      event.preventDefault();
      event.stopImmediatePropagation();

      showConfirm(extractConfirmMessage(handler)).then(function (confirmed) {
        if (!confirmed) return;
        form.dataset.examlyConfirmBypass = '1';
        HTMLFormElement.prototype.submit.call(form);
      });
    }, true);
  });
}());
