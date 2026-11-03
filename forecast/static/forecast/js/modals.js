/* QSR Forecast – hệ thống popup dùng chung.
 * Mỗi popup trong thiết kế được dựng từ 7 kiểu: alert, loading, info, choice, confirm, form, calendar/table.
 * Các nút kích hoạt popup khai báo bằng data-act="..."; luồng xử lý nằm trong ACTIONS bên dưới.
 * Phần "giả lập máy chủ" (later/flow) cần thay bằng gọi API Django khi có backend. */
(function () {
  'use strict';

  var DEMO_DATE = '31/10/2025';
  var URLS = window.QSR_URLS || {};
  var ROLE = document.body.getAttribute('data-role') || 'manager';


  var CHOICES = {
    accounts: { title: 'Chọn tài khoản đăng nhập', get options() {
      return (window.QSR_ACCOUNTS || []).map(function (a) { return { label: a.label, value: a.value }; });
    } },
    reason: { title: 'Chọn lý do điều chỉnh', options: ['Sự kiện tại cửa hàng', 'Khuyến mãi', 'Thay đổi giờ phục vụ', 'Khác'] },
    period: { title: 'Chọn kỳ báo cáo', options: ['01/01/2025 – 30/10/2025', '01/11/2025 – 30/11/2025'] },
    safety: { title: 'Chọn mức an toàn', options: ['90%', '95%', '99%'] },
    deadline: { title: 'Chọn hạn chuẩn bị', options: ['09:00', '10:00', '11:00'] },
    remind: { title: 'Chọn giờ nhắc kiểm kho', options: ['20:00', '21:00', '22:00'] },
    datagroup: { title: 'Chọn nhóm dữ liệu nhập', options: ['Bán hàng hằng ngày', 'Khuyến mãi', 'Thời tiết', 'Ngày lễ & sự kiện'] },
    importmode: { title: 'Chọn cách nhập dữ liệu', options: ['Thêm dữ liệu mới', 'Cập nhật theo khóa'] },
    runstore: { title: 'Chọn cửa hàng chạy dự báo', get options() { return (window.QSR_DATA || {}).stores || []; } },
    manager: { title: 'Chọn quản lý phụ trách', hint: 'Phân công mới sẽ thay thế cửa hàng phụ trách hiện tại của quản lý.',
      get options() { return (window.QSR_DATA || {}).managers || ['Chưa gán']; } },
    role: { title: 'Chọn vai trò tài khoản', options: ['Nhân viên bếp/kho', 'Quản lý cửa hàng', 'Quản trị viên'] },
    scope: { title: 'Chọn phạm vi tài khoản', hint: 'Cuộn danh sách để xem thêm',
      get options() { return (window.QSR_DATA || {}).scopes || ['Toàn hệ thống']; } }
  };

  /* ---------- tiện ích ---------- */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function later(fn, ms) { return setTimeout(fn, ms || 900); }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function fmt(d, m, y) { return pad(d) + '/' + pad(m) + '/' + y; }
  function parseDate(s) {
    var p = String(s).split('/');
    return { d: +p[0], m: +p[1], y: +p[2] };
  }
  function go(name) { if (URLS[name]) window.location.href = URLS[name]; }

  var ICONS = {
    error: '<svg class="w-8 h-8 text-[#E5484D]" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path stroke-linecap="round" d="M9 9l6 6M15 9l-6 6"/></svg>',
    success: '<svg class="w-8 h-8 text-forest" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path stroke-linecap="round" stroke-linejoin="round" d="M8 12.5l2.7 2.7L16 9.5"/></svg>',
    warning: '<svg class="w-8 h-8 text-[#D98E04]" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path stroke-linecap="round" d="M12 7.5v5M12 16v.01"/></svg>',
    spinner: '<svg class="w-8 h-8 text-ink/70 animate-spin" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" d="M12 3a9 9 0 109 9"/></svg>'
  };
  var ICON_BG = { error: 'bg-[#FDECEC]', success: 'bg-[#E9F6F0]', warning: 'bg-[#F4F4F1]', spinner: 'bg-[#F4F4F1]' };
  var X_BTN = '<button type="button" data-x aria-label="Đóng" class="w-8 h-8 grid place-items-center text-ink/60 hover:text-ink text-xl leading-none">×</button>';

  /* ---------- lớp nền + vòng đời ---------- */
  var root = null;
  var current = null;

  function ensureRoot() {
    if (root) return;
    root = document.createElement('div');
    root.id = 'qsr-modal-root';
    document.body.appendChild(root);
    root.addEventListener('mousedown', function (e) {
      if (e.target.hasAttribute('data-backdrop') && current && !current.locked) close();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && current && !current.locked) close();
    });
  }

  function open(html, o) {
    o = o || {};
    ensureRoot();
    root.innerHTML =
      '<div data-backdrop class="fixed inset-0 z-50 grid place-items-center bg-ink/60 p-4">' +
      '<div role="dialog" aria-modal="true" class="bg-white rounded-3xl shadow-2xl w-full max-h-[90vh] overflow-y-auto ' +
      (o.width || 'max-w-[480px]') + '">' + html + '</div></div>';
    current = { onClose: o.onClose, locked: !!o.locked };
    document.body.classList.add('overflow-hidden');
    var card = $('[role=dialog]', root);
    $$('[data-x]', card).forEach(function (b) { b.onclick = function () { close(); }; });
    return card;
  }

  function close(silent) {
    if (!root || !current) return;
    var c = current;
    current = null;
    root.innerHTML = '';
    document.body.classList.remove('overflow-hidden');
    if (!silent && c.onClose) c.onClose();
  }

  var BTN = {
    primary: 'bg-[#0A0A0A] text-white hover:bg-black',
    ghost: 'border border-ink/15 bg-white text-ink hover:bg-page',
    danger: 'bg-[#F0505A] text-white hover:bg-[#e03f49]'
  };

  /* Gắn nút hành động: run() chạy trước; nếu popup không bị thay thế và run không trả false thì tự đóng. */
  function bindActions(card, actions, meCtx) {
    $$('[data-i]', card).forEach(function (b) {
      b.onclick = function () {
        var a = actions[+b.getAttribute('data-i')];
        var me = current;
        var r = a.run ? a.run(card) : undefined;
        if (r !== false && current === me) close();
      };
    });
  }

  function actionBtns(actions, size) {
    var big = size === 'big';
    var cls = big ? 'h-12 rounded-xl text-base' : 'h-10 px-4 rounded-lg text-sm';
    var layout = big
      ? (actions.length > 1 ? 'grid grid-cols-' + actions.length + ' gap-3' : '')
      : 'flex justify-end gap-2';
    return '<div class="' + layout + '">' + actions.map(function (a, i) {
      return '<button type="button" data-i="' + i + '" class="' + cls + ' font-medium ' + (big ? 'w-full ' : '') +
        BTN[a.kind || 'primary'] + '">' + esc(a.label) + '</button>';
    }).join('') + '</div>';
  }

  /* ---------- các kiểu popup ---------- */
  function alertBox(o) {
    var actions = o.actions || [{ label: 'Đóng', kind: 'primary' }];
    var card = open(
      '<div class="p-8 text-center">' +
      '<span class="w-16 h-16 rounded-full grid place-items-center mx-auto mb-5 ' + ICON_BG[o.type || 'error'] + '">' + ICONS[o.type || 'error'] + '</span>' +
      '<h2 class="text-2xl font-medium mb-3">' + esc(o.title) + '</h2>' +
      '<p class="text-ink/60 text-base leading-7 mb-6">' + esc(o.text) + '</p>' +
      actionBtns(actions, 'big') + '</div>',
      { onClose: o.onClose, width: o.width || 'max-w-[440px]' });
    bindActions(card, actions);
    return card;
  }

  function loading(o) {
    return open(
      '<div class="p-8 text-center">' +
      '<span class="w-16 h-16 rounded-full grid place-items-center mx-auto mb-5 bg-[#F4F4F1]">' + ICONS.spinner + '</span>' +
      '<h2 class="text-2xl font-medium mb-3">' + esc(o.title) + '</h2>' +
      '<p class="text-ink/60 text-base leading-7">' + esc(o.text) + '</p></div>',
      { locked: true, width: 'max-w-[440px]' });
  }

  /* Hiển thị loading rồi gọi next() (giả lập chờ máy chủ). */
  function flow(l, next, ms) {
    loading(l);
    var me = current;
    later(function () { if (current === me) next(); }, ms);
  }

  function info(o) {
    var actions = o.actions || [];
    var rows = (o.rows || []).map(function (r) {
      return '<div class="flex justify-between gap-6 py-1.5 text-sm"><span class="text-ink/60">' + esc(r[0]) +
        '</span><span class="text-right">' + esc(r[1]) + '</span></div>';
    }).join('');
    var head = o.closeBtn
      ? '<button type="button" data-x class="h-10 px-5 rounded-lg border border-ink/15 text-sm font-medium">Đóng</button>'
      : X_BTN;
    var card = open(
      '<div class="p-6"><div class="flex items-start justify-between mb-3">' +
      '<h2 class="text-lg font-medium">' + esc(o.title) + '</h2>' + head + '</div>' +
      rows + (o.html || '') +
      (o.note ? '<p class="text-sm text-ink/60 mt-2">' + esc(o.note) + '</p>' : '') +
      (actions.length ? '<div class="mt-4">' + actionBtns(actions) + '</div>' : '') + '</div>',
      { onClose: o.onClose, width: o.width });
    bindActions(card, actions);
    return card;
  }

  function choice(o) {
    var opts = o.options.map(function (x) { return typeof x === 'string' ? { label: x, value: x } : x; });
    var card = open(
      '<div class="p-6"><div class="flex items-center justify-between mb-4"><h2 class="text-lg font-medium">' + esc(o.title) +
      '</h2>' + X_BTN + '</div>' +
      (o.hint ? '<p class="text-sm text-ink/60 mb-3">' + esc(o.hint) + '</p>' : '') +
      '<div class="flex flex-col gap-2.5">' + opts.map(function (x, i) {
        return '<button type="button" data-o="' + i + '" class="h-11 rounded-lg border border-ink/15 bg-white text-sm hover:bg-page">' + esc(x.label) + '</button>';
      }).join('') + '</div></div>',
      { onClose: o.onCancel });
    $$('[data-o]', card).forEach(function (b) {
      b.onclick = function () {
        var me = current;
        o.onPick(opts[+b.getAttribute('data-o')].value);
        if (current === me) close(true);
      };
    });
    return card;
  }

  function table(o) {
    var head = '<tr>' + o.cols.map(function (c) { return '<th class="text-left font-normal px-3 py-2.5">' + esc(c) + '</th>'; }).join('') + '</tr>';
    var body = o.rows.map(function (r) {
      return '<tr class="border-t border-ink/10">' + r.map(function (c, i) {
        var cls = (o.right && o.right.indexOf(i) > -1) ? ' text-right' : '';
        var color = (o.green && o.green === i + 1) ? ' text-forest' : '';
        return '<td class="px-3 py-2.5' + cls + color + '">' + esc(c) + '</td>';
      }).join('') + '</tr>';
    }).join('');
    return info({
      title: o.title, rows: o.meta, width: 'max-w-[900px]',
      html: '<table class="w-full text-sm mt-3"><thead class="bg-[#EAEEEC] text-ink/70">' + head + '</thead><tbody>' + body + '</tbody></table>',
      note: o.note, actions: o.actions
    });
  }

  /* Form: field {name,label,type:'text'|'textarea'|'select',pick:key,placeholder,required}. */
  function form(o, values) {
    values = values || o.values || {};
    var fields = o.fields.map(function (f) {
      var v = values[f.name] != null ? values[f.name] : (f.value || '');
      var label = '<label class="block text-sm text-ink/70 mb-1.5">' + esc(f.label) + (f.required ? ' *' : '') + '</label>';
      var ctl;
      if (f.type === 'select') {
        ctl = '<button type="button" data-f="' + esc(f.name) + '" data-pick="' + esc(f.pick) + '" data-value="' + esc(v) + '" ' +
          'class="w-full h-11 rounded-lg border border-ink/20 px-3 text-sm flex items-center justify-between text-left">' +
          '<span>' + esc(v || f.placeholder || 'Chọn') + '</span><svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M6 9l6 6 6-6"/></svg></button>';
      } else if (f.type === 'textarea') {
        ctl = '<textarea data-f="' + esc(f.name) + '" rows="4" placeholder="' + esc(f.placeholder || '') +
          '" class="w-full rounded-lg border border-ink/20 px-3 py-2 text-sm">' + esc(v) + '</textarea>';
      } else {
        ctl = '<input data-f="' + esc(f.name) + '" type="' + (f.inputType || 'text') + '" value="' + esc(v) + '" placeholder="' +
          esc(f.placeholder || '') + '"' + (f.readonly ? ' readonly' : '') + ' class="w-full h-11 rounded-lg border border-ink/20 px-3 text-sm' + (f.readonly ? ' bg-page text-ink/60' : '') + '">';
      }
      return '<div class="mb-3">' + label + ctl + '</div>';
    }).join('');
    var actions = [{ label: 'Hủy', kind: 'ghost' }, {
      label: o.submit, kind: 'primary',
      run: function (card) { return o.onSubmit(collect(card), card); }
    }];
    var card = open(
      '<div class="p-6"><div class="flex items-center justify-between mb-4"><h2 class="text-lg font-medium">' + esc(o.title) + '</h2>' + X_BTN + '</div>' +
      fields + (o.extra || '') + '<div class="mt-4">' + actionBtns(actions) + '</div></div>',
      { onClose: o.onCancel, width: o.width });
    bindActions(card, actions);
    $$('[data-pick]', card).forEach(function (b) {
      b.onclick = function () {
        var vals = collect(card);
        var back = function () { form(o, vals); };
        var ch = CHOICES[b.getAttribute('data-pick')];
        choice({
          title: ch.title, hint: ch.hint, options: ch.options, onCancel: back,
          onPick: function (v) { vals[b.getAttribute('data-f')] = v; form(o, vals); }
        });
      };
    });
    if (o.afterOpen) o.afterOpen(card);
    return card;
  }

  function collect(card) {
    var v = {};
    $$('[data-f]', card).forEach(function (el) {
      v[el.getAttribute('data-f')] = el.hasAttribute('data-pick') ? el.getAttribute('data-value') : el.value;
    });
    return v;
  }

  /* ---------- lịch ---------- */
  var DOW = ['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'];

  function monthGrid(y, m, cell) {
    var first = new Date(y, m - 1, 1);
    var offset = (first.getDay() + 6) % 7;
    var days = new Date(y, m, 0).getDate();
    var out = '';
    for (var i = 0; i < offset; i++) out += '<span></span>';
    for (var d = 1; d <= days; d++) out += cell(d);
    return '<div class="grid grid-cols-7 gap-y-1 text-center text-sm">' +
      DOW.map(function (n) { return '<span class="text-ink/60 py-2">' + n + '</span>'; }).join('') + out + '</div>';
  }

  function arrow(dir, disabled, id) {
    return '<button type="button" id="' + id + '" ' + (disabled ? 'disabled' : '') +
      ' class="w-9 h-9 rounded-lg border border-ink/15 grid place-items-center ' + (disabled ? 'opacity-30' : '') + '">' + (dir < 0 ? '‹' : '›') + '</button>';
  }

  /* Chọn 1 ngày (tháng 09–11/2025). */
  function calendar(o) {
    var sel = parseDate(o.selected);
    var view = { y: sel.y, m: sel.m };
    var min = o.min || { y: 2025, m: 9 }, max = o.max || { y: 2025, m: 11 };
    var picked = { d: sel.d, m: sel.m, y: sel.y };
    function render() {
      var atMin = view.y === min.y && view.m === min.m, atMax = view.y === max.y && view.m === max.m;
      var grid = monthGrid(view.y, view.m, function (d) {
        var on = picked.d === d && picked.m === view.m && picked.y === view.y;
        return '<button type="button" data-day="' + d + '" class="mx-auto w-9 h-9 rounded-full ' +
          (on ? 'bg-ink text-white' : 'hover:bg-page') + '">' + d + '</button>';
      });
      var actions = [{ label: 'Hủy', kind: 'ghost' }, {
        label: 'Áp dụng', kind: 'primary',
        run: function () { o.onApply(fmt(picked.d, picked.m, picked.y)); }
      }];
      var card = open(
        '<div class="p-6"><div class="flex items-center justify-between mb-4"><h2 class="text-base font-medium">' + esc(o.title) + ' · ' + pad(view.m) + '/' + view.y +
        '</h2>' + X_BTN + '</div><div class="flex items-center justify-between mb-2">' + arrow(-1, atMin, 'cal-prev') +
        '<span class="text-sm font-medium">Tháng ' + view.m + '/' + view.y + '</span>' + arrow(1, atMax, 'cal-next') + '</div>' +
        '<p class="text-sm text-ink/60 mb-1">' + fmt(picked.d, picked.m, picked.y) + '</p>' + grid +
        '<div class="mt-4">' + actionBtns(actions) + '</div></div>', { width: 'max-w-[360px]' });
      bindActions(card, actions);
      $$('[data-day]', card).forEach(function (b) {
        b.onclick = function () { picked = { d: +b.getAttribute('data-day'), m: view.m, y: view.y }; render(); };
      });
      var shift = function (n) {
        view.m += n;
        if (view.m < 1) { view.m = 12; view.y--; }
        if (view.m > 12) { view.m = 1; view.y++; }
        render();
      };
      var p = $('#cal-prev', card), n = $('#cal-next', card);
      if (!atMin) p.onclick = function () { shift(-1); };
      if (!atMax) n.onclick = function () { shift(1); };
    }
    render();
  }

  /* Chọn khoảng ngày (kỳ dữ liệu 01/01/2021 – 30/10/2025). */
  function rangeCalendar(o) {
    var min = { y: 2021, m: 1 }, max = { y: 2025, m: 10 }, lastDay = { y: 2025, m: 10, d: 30 };
    var cur = o.value.split(' – ').map(parseDate);
    var from = cur[0], to = cur[1];
    var view = { y: max.y, m: max.m };
    function num(x) { return x.y * 10000 + x.m * 100 + x.d; }
    function render() {
      var atMin = view.y === min.y && view.m === min.m, atMax = view.y === max.y && view.m === max.m;
      var grid = monthGrid(view.y, view.m, function (d) {
        var dt = { y: view.y, m: view.m, d: d };
        var disabled = num(dt) > num(lastDay);
        var inRange = from && to && num(dt) >= num(from) && num(dt) <= num(to);
        return '<button type="button" ' + (disabled ? 'disabled' : 'data-day="' + d + '"') + ' class="mx-auto w-9 h-9 rounded-lg ' +
          (disabled ? 'text-ink/25' : inRange ? 'bg-[#DDF2EA]' : 'hover:bg-page') + '">' + d + '</button>';
      });
      var actions = [{ label: 'Hủy', kind: 'ghost' }, {
        label: 'Áp dụng', kind: 'primary',
        run: function () { o.onApply(fmt(from.d, from.m, from.y) + ' – ' + fmt(to.d, to.m, to.y)); }
      }];
      var card = open(
        '<div class="p-6"><div class="flex items-center justify-between mb-3"><h2 class="text-base font-medium">Chọn kỳ dữ liệu</h2>' + X_BTN + '</div>' +
        '<div class="inline-block rounded-lg border border-ink/20 px-3 py-2 text-sm mb-3">' + fmt(from.d, from.m, from.y) + ' &nbsp;–&nbsp; ' +
        (to ? fmt(to.d, to.m, to.y) : '…') + '</div>' +
        '<div class="flex items-center justify-between mb-1">' + arrow(-1, atMin, 'cal-prev') +
        '<span class="text-sm font-medium">Tháng ' + view.m + ' / ' + view.y + '</span>' + arrow(1, atMax, 'cal-next') + '</div>' + grid +
        '<button type="button" id="cal-all" class="w-full h-10 mt-3 rounded-lg border border-ink/15 text-sm">Toàn bộ dữ liệu</button>' +
        '<div class="mt-3">' + actionBtns(actions) + '</div></div>', { width: 'max-w-[380px]' });
      bindActions(card, actions);
      var picking = false;
      $$('[data-day]', card).forEach(function (b) {
        b.onclick = function () {
          var dt = { y: view.y, m: view.m, d: +b.getAttribute('data-day') };
          if (!picking) { from = dt; to = dt; picking = true; }
          else { if (num(dt) < num(from)) { to = from; from = dt; } else { to = dt; } picking = false; }
          render();
        };
      });
      $('#cal-all', card).onclick = function () { from = { d: 1, m: 1, y: 2021 }; to = { d: 30, m: 10, y: 2025 }; render(); };
      var shift = function (n) {
        view.m += n;
        if (view.m < 1) { view.m = 12; view.y--; }
        if (view.m > 12) { view.m = 1; view.y++; }
        render();
      };
      if (!atMin) $('#cal-prev', card).onclick = function () { shift(-1); };
      if (!atMax) $('#cal-next', card).onclick = function () { shift(1); };
    }
    render();
  }

  /* ---------- gọi API Django ---------- */
  var API = window.QSR_API || {};
  var WHO = document.body.getAttribute('data-user') || '';
  var STORE = document.body.getAttribute('data-store') || '';

  function csrfToken() { var m = document.querySelector('meta[name=csrf-token]'); return m ? m.content : ''; }
  function request(method, url, data) {
    var opt = { method: method, credentials: 'same-origin', headers: { 'X-CSRFToken': csrfToken() } };
    if (data !== undefined) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(data); }
    return fetch(url, opt).then(function (r) {
      if (r.status === 401 && URLS.login) { window.location.href = URLS.login; }
      return r.json().catch(function () { return { ok: false, error: 'bad_response', message: 'Phản hồi không hợp lệ từ máy chủ.' }; })
        .then(function (j) { j.httpStatus = r.status; return j; });
    }).catch(function () { return { ok: false, error: 'network', message: 'Không kết nối được máy chủ.' }; });
  }
  function post(url, data) { return request('POST', url, data || {}); }
  function getJson(url) { return request('GET', url); }
  function planUrl(id, action) { return '/api/plan/' + id + '/' + (action ? action + '/' : ''); }
  function reload() { window.location.reload(); }
  function thousand(n) { return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, '.'); }

  /* Hiện loading (tối thiểu 400 ms cho khỏi nháy) rồi gọi next(kết quả). */
  function withLoading(l, promise, next) {
    loading(l);
    var me = current, t0 = Date.now();
    promise.then(function (res) {
      setTimeout(function () { if (current === me) next(res); }, Math.max(0, 400 - (Date.now() - t0)));
    });
  }
  function failBox(res, title, onClose) {
    alertBox({ type: 'error', title: title, text: res.message || 'Đã có lỗi xảy ra.', onClose: onClose });
  }
  /* Gửi form GET thật sau một nhịp loading. */
  function goSubmit(f, title, text) {
    loading({ title: title, text: text });
    setTimeout(function () { f.submit(); }, 250);
  }
  function addDay(text, n) {
    var d = parseDate(text), t = new Date(d.y, d.m - 1, d.d + n);
    return fmt(t.getDate(), t.getMonth() + 1, t.getFullYear());
  }

  /* ---------- luồng chạy dự báo / duyệt (quản lý) ---------- */
  function reopenConfirm(planId, date) {
    alertBox({
      type: 'error', title: 'Mở lại danh sách đã duyệt?', width: 'max-w-[480px]',
      text: 'Mở lại để điều chỉnh hoặc chạy dự báo mới. Bếp tiếp tục xem danh sách đã duyệt gần nhất; danh sách mới chỉ gửi đến bếp sau khi quản lý duyệt lại.',
      actions: [{ label: 'Hủy', kind: 'ghost' }, { label: 'Mở lại danh sách', kind: 'primary', run: function () {
        withLoading({ title: 'Đang mở lại danh sách', text: 'Vui lòng đợi.' }, post(planUrl(planId, 'reopen')), function (res) {
          if (res.ok) runForecast(date); else failBox(res, 'Không thể mở lại danh sách');
        });
        return false;
      } }]
    });
  }

  function runForecast(date) {
    withLoading({ title: 'Đang chạy dự báo', text: 'Đang tính dự báo theo món cho cửa hàng ' + STORE.split(' ')[0] + ' · Ngày: ' + date },
      post(API.run, { date: date }), function (res) {
        if (res.ok) {
          var p = res.plan;
          return info({
            title: 'Dự báo đã hoàn tất', onClose: reload,
            rows: [['Cửa hàng', STORE], ['Ngày dự báo', date], ['Tổng dự báo', thousand(p.forecast_total) + ' phần'], ['Phạm vi', p.lines + ' món'],
              ['Thiếu hàng · Cần bổ sung', p.short + ' · ' + p.topup], ['Đề xuất chuẩn bị', 'Chờ duyệt']]
          });
        }
        if (res.error === 'approved') {
          return alertBox({
            type: 'error', title: 'Đã duyệt – không chạy lại dự báo', width: 'max-w-[480px]',
            text: 'Danh sách ngày ' + date + ' đã được duyệt. Muốn chạy lại, quản lý cần mở lại danh sách; bếp sẽ nhận danh sách mới sau khi duyệt lại.',
            actions: [{ label: 'Chạy lại', kind: 'primary', run: function () { reopenConfirm(res.plan_id, date); return false; } }]
          });
        }
        var retry = res.error === 'no_data' || res.error === 'server_error';
        alertBox({
          type: 'error', title: 'Không thể chạy dự báo',
          text: res.error === 'no_data' ? 'Không có dữ liệu đầu vào cho ngày đã chọn · Kiểm tra ngày và dữ liệu bán hàng.' : res.message,
          actions: retry ? [{ label: 'Chạy lại', kind: 'primary', run: function () { runForecast(date); return false; } }] : undefined
        });
      });
  }

  /* ---------- hành động gắn data-act (dữ liệu thật) ---------- */
  var LIVE_ACTIONS = {
    notif: function () {
      getJson(API.notifications).then(function (res) {
        if (!res.ok) return failBox(res, 'Không tải được thông báo');
        var title = ROLE === 'staff' ? 'Thông báo · Nhân viên bếp/kho' : ROLE === 'admin' ? 'Thông báo · Quản trị viên' : 'Tất cả thông báo';
        var list = res.items.length ? res.items.map(function (n) {
          return '<div class="flex items-center justify-between py-2.5"><div><div class="text-sm ' + (n.read ? '' : 'font-medium') + '">' + esc(n.title) +
            '</div><div class="text-xs text-ink/60 mt-0.5">' + esc(n.detail) + '</div></div>' +
            (n.link && URLS[n.link] ? '<span class="flex gap-2"><button type="button" data-go="' + esc(n.link) + '" class="h-9 px-4 rounded-lg border border-ink/20 text-sm">' + (ROLE === 'staff' && n.link === 'staff_prep' ? 'Mở danh sách chuẩn bị' : 'Xem') + '</button>' +
            (ROLE === 'staff' && n.link === 'staff_prep' ? '<button type="button" data-go="inventory" class="h-9 px-4 rounded-lg border border-ink/20 text-sm">Mở kiểm kho</button>' : '') + '</span>' : '') + '</div>';
        }).join('') : '<p class="text-sm text-ink/60 py-4">Chưa có thông báo nào.</p>';
        var card = info({ title: title, width: 'max-w-[640px]', rows: [],
          html: '<button type="button" id="mark-read" class="h-9 px-4 rounded-lg border border-ink/20 text-sm my-2">Đánh dấu tất cả đã đọc</button>' + list });
        card.addEventListener('click', goHandler);
        $('#mark-read', card).onclick = function () {
          post(API.readNotifications).then(function () { var b = $('#notif-badge'); if (b) b.hidden = true; close(); });
        };
      });
    },

    'login-submit': function (f) {
      var req = fetch(f.action, { method: 'POST', body: new FormData(f), credentials: 'same-origin' })
        .then(function (r) { return r.json(); }).catch(function () { return { ok: false }; });
      withLoading({ title: 'Đang đăng nhập', text: 'Đang xác thực tài khoản ' + f.elements.username.value + '.' }, req, function (res) {
        if (res.ok) window.location.href = res.next;
        else alertBox({ type: 'error', title: 'Không thể đăng nhập', text: res.error === 'locked' ? 'Đăng nhập sai quá nhiều lần · Thử lại sau 15 phút.' : 'Tên đăng nhập hoặc mật khẩu không hợp lệ · Kiểm tra thông tin và thử lại.' });
      });
    },
    'reset-pw': function () {
      var sel = $('#username');
      form({
        title: 'Yêu cầu cấp lại mật khẩu', submit: 'Ghi nhận yêu cầu',
        fields: [{ name: 'user', label: 'Tên đăng nhập', value: sel ? sel.value : '' }],
        extra: '<p class="text-sm text-ink/60 -mt-1">Quản trị viên sẽ kiểm tra tài khoản và cấp lại mật khẩu.</p>',
        onSubmit: function (v) {
          if (!v.user.trim()) { $('[data-f=user]').classList.add('border-[#E5484D]'); return false; }
          withLoading({ title: 'Đang gửi yêu cầu', text: 'Vui lòng đợi.' }, post(API.passwordReset, { username: v.user.trim() }), function (res) {
            if (res.ok) alertBox({ type: 'success', title: 'Yêu cầu cấp lại mật khẩu đã được ghi nhận', width: 'max-w-[480px]',
              text: 'Trạng thái: Chờ xử lý · Người xử lý: Quản trị viên · ' + res.at });
            else failBox(res, 'Không thể gửi yêu cầu');
          });
        }
      });
    },
    'profile-pw': function (f) {
      var data = { current: f.elements.current.value, 'new': f.elements.next.value, again: f.elements.again.value };
      withLoading({ title: 'Đang cập nhật mật khẩu', text: 'Vui lòng đợi.' }, post(API.password, data), function (res) {
        if (!res.ok) return failBox(res, 'Không thể cập nhật mật khẩu');
        f.reset();
        alertBox({ type: 'success', title: 'Mật khẩu đã được cập nhật' + (ROLE === 'staff' ? ' · NV' : ROLE === 'admin' ? ' · QTV' : ''),
          text: 'Trạng thái: Đã lưu · ' + WHO + ' · ' + res.at });
      });
    },

    'view-data': function (f) { goSubmit(f, 'Đang tải dữ liệu', 'Đang tải dữ liệu theo ngày đã chọn.'); },
    'view-forecast': function (f) { goSubmit(f, 'Đang tải dự báo', 'Ngày dự báo: ' + f.elements.date.value); },
    'view-inventory': function (f) { goSubmit(f, 'Đang tải dữ liệu', 'Đang tải dữ liệu theo ngày đã chọn.'); },
    'view-report': function (f) { goSubmit(f, 'Đang tải báo cáo', 'Đang tổng hợp doanh thu và lượng bán theo kỳ lọc.'); },

    'prep-run': function (el) { runForecast(el.getAttribute('data-date')); },
    'none-ok': function () { alertBox({ type: 'warning', title: 'Không cần chuẩn bị thêm', text: 'Không có món đủ hàng · 0 món' }); },
    'prep-approve': function (el) {
      var id = el.getAttribute('data-plan'), date = el.getAttribute('data-date');
      getJson(planUrl(id)).then(function (res) {
        if (!res.ok) return failBox(res, 'Không tải được đề xuất');
        var p = res.plan;
        if (p.status === 'approved') {
          return info({ title: 'Danh sách đã được duyệt', closeBtn: true, rows: [
            ['Trạng thái', 'Đã duyệt'], ['Cửa hàng', res.store_name], ['Ngày phục vụ', date],
            ['Phạm vi', p.lines + ' món cần chuẩn bị · Áp dụng ' + thousand(p.applied_total) + ' phần'],
            ['Người thực hiện', res.approved_by], ['Thời điểm', res.approved_at]] });
        }
        info({
          title: 'Duyệt danh sách chuẩn bị', closeBtn: true, width: 'max-w-[560px]',
          rows: [['Cửa hàng', res.store_name], ['Ngày phục vụ', date], ['Người duyệt', WHO],
            ['Phạm vi', 'Toàn bộ ' + p.lines + ' món cần chuẩn bị'], ['Phân loại', p.short + ' thiếu hàng · ' + p.topup + ' cần bổ sung']],
          html: '<div class="rounded-xl bg-[#F4F5F4] p-4 mt-3 text-sm"><div class="text-ink/60">Đề xuất gốc: ' + thousand(res.original_total) + ' phần</div>' +
            '<div class="flex justify-between items-end mt-2"><span class="text-ink/70">Tổng sau điều chỉnh</span><span class="text-xl">' + thousand(p.applied_total) + ' phần</span></div></div>',
          actions: [{ label: 'Quay lại kiểm tra', kind: 'ghost' }, { label: 'Duyệt', kind: 'primary', run: function () {
            withLoading({ title: 'Đang duyệt danh sách', text: 'Đang gửi danh sách sang bếp.' }, post(planUrl(id, 'approve')), function (r) {
              if (r.ok) alertBox({ type: 'success', title: 'Danh sách đã được duyệt', width: 'max-w-[480px]', onClose: reload,
                text: p.lines + ' món đã chốt · ' + p.short + ' thiếu hàng · ' + p.topup + ' cần bổ sung. Quản lý cần mở lại trước khi thay đổi.' });
              else failBox(r, 'Không thể duyệt danh sách');
            });
            return false;
          } }]
        });
      });
    },
    'prep-adjust': function (el) {
      var qty = +el.getAttribute('data-applied'), unit = el.getAttribute('data-unit');
      var card = info({
        title: 'Điều chỉnh số lượng · ' + el.getAttribute('data-name'), rows: [],
        html: '<label class="block text-sm text-ink/70 mt-2 mb-2">Số lượng cần chuẩn bị</label>' +
          '<div class="flex items-center gap-2"><button type="button" id="q-minus" class="w-12 h-11 rounded-lg border border-ink/20">−</button>' +
          '<div id="q-val" class="flex-1 h-11 rounded-lg border border-ink/20 grid place-items-center">' + qty + ' ' + esc(unit) + '</div>' +
          '<button type="button" id="q-plus" class="w-12 h-11 rounded-lg border border-ink/20">+</button></div>',
        actions: [{ label: 'Hủy', kind: 'ghost' }, { label: 'Lưu số lượng', kind: 'primary', run: function () {
          withLoading({ title: 'Đang lưu số lượng', text: 'Vui lòng đợi.' }, post('/api/line/' + el.getAttribute('data-line') + '/qty/', { qty: qty }), function (res) {
            if (!res.ok) return failBox(res, 'Không thể lưu số lượng');
            el.setAttribute('data-applied', qty); el.textContent = qty; close();
          });
          return false;
        } }]
      });
      var show = function () { $('#q-val', card).textContent = qty + ' ' + unit; };
      $('#q-minus', card).onclick = function () { if (qty > 0) { qty--; show(); } };
      $('#q-plus', card).onclick = function () { qty++; show(); };
    },

    'fc-list': function (el) {
      getJson(planUrl(el.getAttribute('data-plan'))).then(function (res) {
        if (!res.ok) return failBox(res, 'Không tải được dự báo');
        table({
          title: 'Dự báo theo món · ' + (res.plan.service_date.split('-').reverse().join('/')),
          meta: [['Tổng dự báo', thousand(res.plan.forecast_total) + ' phần · Trạng thái: ' + (res.plan.adjustment_pct ? 'Đã điều chỉnh ' + res.plan.adjustment_pct + '%' : 'Chưa điều chỉnh')]],
          cols: ['Món', 'Dự báo', 'Bình thường', 'Chênh lệch'], right: [1, 2, 3],
          rows: res.lines.map(function (l) {
            return [l.name + ' ' + l.unit, l.forecast, l.baseline, l.diff > 0 ? '↑ Nhiều hơn ' + l.diff + '%' : l.diff < 0 ? '↓ Ít hơn ' + Math.abs(l.diff) + '%' : 'Tương đương'];
          }),
          note: '"Bình thường": Trung bình 7 ngày liền trước'
        });
      });
    },
    'fc-save': function (el) {
      var id = el.getAttribute('data-plan'), pct = +$('#fc-pct').value, sel = $('#fc-reason');
      var reason = sel.value === 'Chọn lý do' ? '' : sel.value;
      var doSave = function (r) {
        withLoading({ title: 'Đang lưu điều chỉnh', text: 'Đang tính lại số lượng cần chuẩn bị.' }, post(planUrl(id, 'adjust'), { pct: pct, reason: r }), function (res) {
          if (res.ok) info({ title: 'Điều chỉnh dự báo đã được lưu', onClose: reload,
            rows: [['Tổng dự báo', thousand(res.plan.forecast_total) + ' phần'], ['Lý do', r || 'Không có']] });
          else failBox(res, 'Chưa thể lưu điều chỉnh');
        });
      };
      if (pct !== 0 && !reason) {
        return choice({ title: CHOICES.reason.title, options: CHOICES.reason.options, onPick: function (v) {
          var pick = function (t) {
            var o = Array.prototype.find.call(sel.options, function (x) { return x.value === t; }) || new Option(t, t);
            if (!o.parentNode) sel.add(o);
            sel.value = t; doSave(t);
          };
          if (v === 'Khác') ACTIONS['other-reason'](pick); else pick(v);
        } });
      }
      doSave(reason);
    },

    'inv-save-draft': function () {
      var s = window.QSR_INV.status(), date = $('[data-calendar=inventory]').value;
      withLoading({ title: 'Đang lưu nháp', text: 'Đang lưu số lượng đã nhập.' }, post(API.saveInventory, { date: date, quantities: s.quantities, draft: true }), function (res) {
        if (!res.ok) return failBox(res, 'Không thể lưu nháp');
        info({ title: 'Đã lưu nháp kiểm kho', closeBtn: true, rows: [['Trạng thái', 'Đã lưu nháp'], ['Cửa hàng', STORE], ['Ngày kiểm kho', date],
          ['Phạm vi', res.entered + '/' + s.total + ' món đã nhập'], ['Người thực hiện', WHO], ['Thời điểm', res.at]] });
      });
    },
    'inv-cancel': function () {
      alertBox({ type: 'warning', title: 'Hủy thay đổi kiểm kho', text: 'Các thay đổi chưa lưu sẽ bị loại bỏ.',
        actions: [{ label: 'Tiếp tục nhập', kind: 'ghost' }, { label: 'Hủy thay đổi', kind: 'danger', run: reload }] });
    },
    'inv-save': function () {
      var s = window.QSR_INV.status(), date = $('[data-calendar=inventory]').value;
      if (s.missing > 0) {
        return alertBox({ type: 'error', title: 'Kiểm kho chưa đầy đủ', text: 'Còn món chưa nhập số lượng · Hoàn thành kiểm kho trước khi tính lại đề xuất.',
          actions: [{ label: 'Nhập số còn thiếu', kind: 'primary', run: function () { window.QSR_INV.focusMissing(); } }] });
      }
      var save = function () {
        withLoading({ title: 'Đang lưu kiểm kho', text: 'Đang tính lại lượng cần chuẩn bị cho ngày phục vụ ' + addDay(date, 1) + '.' },
          post(API.saveInventory, { date: date, quantities: s.quantities, draft: false }), function (res) {
            if (!res.ok) return failBox(res, 'Chưa thể lưu kiểm kho');
            info({ title: 'Kiểm kho đã được lưu', onClose: reload, rows: [['Ngày kiểm kho', date], ['Trạng thái', 'Đã lưu'],
              ['Đề xuất chuẩn bị', res.plan ? 'Chờ duyệt' : 'Giữ nguyên'], ['Người thực hiện', WHO], ['Thời điểm', res.at]] });
          });
      };
      if (s.review.length) {
        return info({
          title: 'Kiểm tra tồn kho trước khi lưu', closeBtn: true,
          rows: [['Trạng thái', 'Cần kiểm tra'], ['Cửa hàng', STORE], ['Ngày kiểm kho', date],
            ['Món cần kiểm tra', s.review.map(function (r) { return r.name; }).join(', ')], ['Người thực hiện', WHO],
            ['Số lượng còn lại', s.review[0].cur], ['Tồn kỳ trước', s.review[0].prev]],
          actions: [{ label: 'Quay lại sửa', kind: 'ghost' }, { label: 'Xác nhận lưu', kind: 'primary', run: function () { save(); return false; } }]
        });
      }
      save();
    },
    'line-done': function (el) {
      post('/api/line/' + el.getAttribute('data-line') + '/done/', { done: true }).then(function (res) {
        if (res.ok) reload(); else failBox(res, 'Không thể đánh dấu xong');
      });
    }
  };

  /* ---------- hành động gắn data-act ---------- */
  var ACTIONS = {
    /* Chung */
    /* Đăng nhập */
    /* Hồ sơ */
    /* Chọn ngày */
    /* Quản lý · Chuẩn bị hàng */
    'prep-reason': function (el) {
      var d = el.dataset;
      var fc = +d.fc, safe = +d.safe, cur = +d.cur, need = fc + safe - cur, applied = +d.applied || need;
      var short = cur < safe, unit = d.unit;
      var callout = short
        ? '<div class="rounded-lg bg-[#F4AEB2] p-3 my-3 text-sm"><div class="font-medium">Tồn kho thấp hơn mức an toàn ' + (safe - cur) + ' ' + esc(unit) + '</div><div class="text-xs mt-1">Hiện có ' + cur + ' ' + esc(unit) + ' · Mức an toàn: ' + safe + ' ' + esc(unit) + '</div></div>'
        : '<div class="rounded-lg bg-[#F6E3A5] p-3 my-3 text-sm"><div class="font-medium">Tồn kho đã đạt mức an toàn</div><div class="text-xs mt-1">Hiện có ' + cur + ' ' + esc(unit) + ' ≥ ' + safe + ' ' + esc(unit) + ' dự phòng. Vẫn cần chuẩn bị cho lượng bán ngày mai.</div></div>';
      var card = info({
        title: 'Vì sao cần chuẩn bị thêm?', width: 'max-w-[600px]', rows: [],
        html: '<div class="flex justify-between text-sm mb-3"><span>' + esc(d.name) + '</span><span class="text-ink/60 text-xs">' + (($('[data-calendar]') || {}).value || DEMO_DATE) + '</span></div>' +
          '<div class="rounded-xl bg-[#E4F3EE] p-4"><div class="text-xs">Cần chuẩn bị thêm · ' + (short ? 'Thiếu hàng' : 'Cần bổ sung') + '</div>' +
          '<div class="text-3xl my-1">' + need + ' ' + esc(unit) + '</div><div class="text-xs text-ink/70">Đáp ứng lượng bán dự kiến và giữ đủ dự phòng.</div></div>' +
          '<div class="grid grid-cols-3 gap-3 my-3 text-sm">' +
          [['Dự kiến bán', fc], ['Giữ dự phòng', safe], ['Tổng cần có', fc + safe]].map(function (c) {
            return '<div class="rounded-lg border border-ink/10 p-3"><div class="text-xs text-ink/70">' + c[0] + '</div><div class="mt-1">' + c[1] + ' ' + esc(unit) + '</div></div>';
          }).join('') + '</div>' +
          '<div class="text-base">' + fc + ' + ' + safe + ' − ' + cur + ' = ' + need + ' ' + esc(unit) + '</div>' +
          '<div class="text-xs text-ink/70 mt-1">Tồn hiện tại: ' + cur + ' ' + esc(unit) + '</div>' +
          '<div class="text-xs text-ink/60">Dự báo và tồn an toàn được làm tròn trước khi cộng trừ.</div>' + callout +
          '<div class="text-sm">Số lượng đang áp dụng: <span class="ml-2">' + applied + ' ' + esc(unit) + '</span></div>'
      });
      if (!d.line) return;
      getJson('/api/line/' + d.line + '/reason/').then(function (res) {
        if (!res.ok || !card.isConnected) return;
        var host = $('.p-6', card);
        host.insertAdjacentHTML('beforeend',
          '<h3 class="text-sm font-medium mt-4 mb-1">Yếu tố ảnh hưởng</h3>' + res.factors.map(function (f) {
            return '<div class="flex justify-between text-sm py-1"><span class="text-ink/60">' + esc(f[0]) + '</span><span>' + esc(f[1]) + '</span></div>';
          }).join('') +
          (res.similar.length ? '<h3 class="text-sm font-medium mt-4 mb-1">Những ngày tương tự trước đây</h3>' + res.similar.map(function (x) {
            return '<div class="flex justify-between text-sm py-1"><span class="text-ink/60">' + esc(x.date) + '</span><span>' + x.qty + ' ' + esc(unit) + '</span></div>';
          }).join('') : ''));
      });
    },
    /* Quản lý · Dự báo */
    'other-reason': function (cb) {
      form({
        title: 'Nhập lý do khác', submit: 'Lưu lý do', width: 'max-w-[480px]',
        fields: [{ name: 'text', label: 'Mô tả lý do điều chỉnh', type: 'textarea', placeholder: 'Nhập lý do cụ thể…', required: true }],
        onSubmit: function (v) {
          if (!v.text.trim()) { $('[data-f=text]').classList.add('border-[#E5484D]'); return false; }
          cb(v.text.trim());
        }
      });
    },

    /* Quản lý · Báo cáo */
    'store-scope': function () {
      alertBox({ type: 'warning', title: 'Phạm vi cửa hàng', text: 'R01 · Downtown Chicago Grill · Phạm vi được cấp cho quản lý hiện tại.' });
    },

    /* Nhân viên · Kiểm kho */
    /* Quản trị · Dữ liệu */
    /* Quản trị · Dự báo & Mô hình */
    /* Quản trị · Cửa hàng */
    /* Quản trị · Tài khoản */
    'acct-search': function (el) {
      var q = el.value || '';
      var names = $$('[data-acct-row]').map(function (r) { return r.getAttribute('data-user'); });
      var card = open(
        '<div class="p-6"><div class="flex items-center justify-between mb-3"><h2 class="text-base font-medium">Tìm tài khoản</h2>' + X_BTN + '</div>' +
        '<label class="block text-sm text-ink/70 mb-1.5">Tên hiển thị hoặc tên đăng nhập</label>' +
        '<input id="s-q" value="' + esc(q) + '" class="w-full h-11 rounded-lg border border-ink/20 px-3 text-sm mb-3">' +
        '<div class="flex flex-col gap-2">' + names.map(function (n) { return '<button type="button" data-n="' + esc(n) + '" class="h-10 rounded-lg border border-ink/15 text-sm hover:bg-page">' + esc(n) + '</button>'; }).join('') + '</div>' +
        '<div class="flex justify-end gap-2 mt-4"><button type="button" id="s-clear" class="h-10 px-4 rounded-lg border border-ink/15 text-sm">Xóa bộ lọc</button>' +
        '<button type="button" id="s-go" class="h-10 px-5 rounded-lg bg-[#0A0A0A] text-white text-sm font-medium">Tìm</button></div></div>', { width: 'max-w-[420px]' });
      var apply = function (v) { el.value = v; el.dispatchEvent(new Event('input')); close(true); };
      $$('[data-n]', card).forEach(function (b) { b.onclick = function () { $('#s-q', card).value = b.getAttribute('data-n'); }; });
      $('#s-clear', card).onclick = function () { apply(''); };
      $('#s-go', card).onclick = function () { apply($('#s-q', card).value); };
    },

    /* Quản trị · Cấu hình */
    'cfg-approval': function () {
      alertBox({ type: 'warning', title: 'Quy trình phê duyệt bắt buộc', text: 'Quản lý phải duyệt trước khi danh sách được chuyển sang giao diện bếp.' });
    }
  };


  /* ---------- hành động của quản trị viên (API thật) ---------- */
  var REQUIRED_COLS = {
    'Bán hàng hằng ngày': 'sale_date · restaurant_id · menu_item_id · quantity',
    'Khuyến mãi': 'promo_date · restaurant_id · menu_item_id',
    'Thời tiết': 'event_date · restaurant_id · avg_temp_f · precip_type',
    'Ngày lễ & sự kiện': 'event_date · restaurant_id (+ is_holiday, holiday_name, is_special_event, special_event_name)'
  };

  function postForm(url, fd) {
    return fetch(url, { method: 'POST', body: fd, credentials: 'same-origin', headers: { 'X-CSRFToken': csrfToken() } })
      .then(function (r) { return r.json(); }).catch(function () { return { ok: false, error: 'network', message: 'Không kết nối được máy chủ.' }; });
  }
  function storeCode(label) { return String(label || '').split(' · ')[0]; }
  function viGroup(list) { return list.length ? list.join(', ') : '—'; }

  var ADMIN_ACTIONS = {
    'filter-data': function (f) { goSubmit(f, 'Đang lọc dữ liệu', 'Đang tải danh sách dữ liệu theo kỳ đã chọn.'); },

    'data-open': function (el) {
      var d = el.dataset;
      var card = info({
        title: 'Dữ liệu · ' + d.name, rows: [['Nhóm dữ liệu', d.name], ['Số dòng', d.rows], ['Phạm vi', d.scope]],
        html: '<p class="text-sm text-ink/60 mt-2">Các trường: ' + esc(d.fields) + '</p>' +
          (d.note ? '<p class="text-sm text-ink/60 mt-2">' + esc(d.note) + '</p>' : '') +
          (d.btn ? '<button type="button" id="grp-btn" class="h-10 px-4 mt-3 rounded-lg border border-ink/20 text-sm">' + (d.btn === 'missing' ? 'Xem các dòng thiếu' : 'Nhập dữ liệu') + '</button>' : '')
      });
      var b = $('#grp-btn', card);
      if (b) b.onclick = function () { d.btn === 'missing' ? ACTIONS['data-missing'](el) : ACTIONS['data-import'](null, d.name); };
    },
    'data-missing': function (el) {
      var range = ($('[data-calendar=range]') || {}).value || '', parts = range.split(' – ');
      var from = (el && el.dataset && el.dataset.from) || parts[0], to = (el && el.dataset && el.dataset.to) || parts[1];
      getJson('/api/admin/data/missing/?from=' + encodeURIComponent(from) + '&to=' + encodeURIComponent(to)).then(function (res) {
        if (!res.ok) return failBox(res, 'Không tải được các dòng thiếu');
        table({
          title: 'Các dòng thiếu số lượng',
          meta: [['Phạm vi', from + ' – ' + to], ['Số dòng thiếu', thousand(res.missing) + ' dòng · ' + String(res.pct).replace('.', ',') + '%']],
          cols: ['Ngày bán', 'Cửa hàng', 'Món'], rows: res.rows.map(function (r) { return [r.date, r.store, r.item]; }),
          note: 'Xử lý: Ước tính số lượng thiếu trước khi chạy dự báo. Hiển thị tối đa 50 dòng đầu.'
        });
      });
    },
    'data-import': function (el, preset) {
      var file = null;
      var o = {
        title: 'Nhập dữ liệu', submit: 'Kiểm tra và xem trước', width: 'max-w-[600px]',
        values: { group: typeof preset === 'string' ? preset : 'Bán hàng hằng ngày', mode: 'Thêm dữ liệu mới' },
        fields: [{ name: 'group', label: 'Nhóm dữ liệu', type: 'select', pick: 'datagroup' }, { name: 'mode', label: 'Cách nhập', type: 'select', pick: 'importmode' }],
        extra: '<label class="block text-sm text-ink/70 mb-1.5">Tệp CSV hoặc Excel</label>' +
          '<div id="imp-name" class="h-11 rounded-lg border border-ink/20 px-3 text-sm flex items-center">Chưa chọn tệp</div>' +
          '<input id="imp-file" type="file" accept=".csv,.xlsx,.xls" hidden>' +
          '<button type="button" id="imp-pick" class="h-9 px-4 mt-2 rounded-lg border border-ink/20 text-sm">Chọn tệp</button>' +
          '<p id="imp-cols" class="text-xs text-ink/60 mt-3"></p>',
        afterOpen: function (card) {
          $('#imp-cols', card).textContent = 'Cột bắt buộc: ' + REQUIRED_COLS[collect(card).group];
          var input = $('#imp-file', card);
          if (file) $('#imp-name', card).textContent = file.name;
          $('#imp-pick', card).onclick = function () { input.click(); };
          input.onchange = function () { file = input.files[0] || null; $('#imp-name', card).textContent = file ? file.name : 'Chưa chọn tệp'; };
        },
        onSubmit: function (v) {
          if (!file || !/\.(csv|xlsx|xls)$/i.test(file.name)) {
            alertBox({ type: 'error', title: 'Chưa thể xem trước dữ liệu', text: 'Chưa chọn tệp hợp lệ · Chọn tệp CSV hoặc Excel để tiếp tục.', onClose: function () { form(o, v); } });
            return;
          }
          var send = function (confirm) {
            var fd = new FormData();
            fd.append('group', v.group); fd.append('mode', v.mode); fd.append('file', file); if (confirm) fd.append('confirm', '1');
            return postForm('/api/admin/data/import/', fd);
          };
          withLoading({ title: 'Đang kiểm tra tệp', text: 'Đang kiểm tra cột và định dạng.' }, send(false), function (res) {
            if (!res.ok) return alertBox({ type: 'error', title: 'Chưa thể xem trước dữ liệu', text: res.message, onClose: function () { form(o, v); } });
            var p = res.preview, ready = p.columns_ok && p.new + p.update > 0;
            var sample = p.sample.length ? '<table class="w-full text-sm mt-3"><tbody>' + [p.columns].concat(p.sample.map(function (r) { return p.columns.map(function (c) { return r[c]; }); })).map(function (r, i) {
              return '<tr class="' + (i ? 'border-t border-ink/10' : 'bg-[#EAEEEC] text-ink/70') + '">' + r.map(function (c) { return '<td class="px-3 py-2">' + esc(c) + '</td>'; }).join('') + '</tr>';
            }).join('') + '</tbody></table>' : '';
            info({
              title: 'Xem trước dữ liệu nhập', width: 'max-w-[760px]',
              rows: [['Tệp', p.file], ['Nhóm dữ liệu', v.group], ['Cách nhập', v.mode],
                ['Kiểm tra cột', p.columns_ok ? 'Đủ cột bắt buộc' : 'Thiếu: ' + viGroup(p.missing_columns)], ['Tổng số dòng', thousand(p.total)],
                ['Sẽ thêm mới · cập nhật', thousand(p.new) + ' · ' + thousand(p.update)], ['Bỏ qua (trùng khóa) · lỗi', thousand(p.skipped) + ' · ' + thousand(p.invalid)]],
              html: sample + (p.errors.length ? '<p class="text-xs text-[#9B1C1C] mt-3">' + p.errors.map(esc).join('<br>') + '</p>' : ''),
              note: 'Chỉ ghi dữ liệu sau khi xác nhận nhập.',
              actions: ready ? [{ label: 'Hủy', kind: 'ghost' }, { label: 'Nhập dữ liệu', kind: 'primary', run: function () {
                withLoading({ title: 'Đang nhập dữ liệu', text: 'Đang kiểm tra định dạng, khóa trùng và ghi dữ liệu hợp lệ.' }, send(true), function (r) {
                  if (!r.ok) return failBox(r, 'Không thể nhập dữ liệu');
                  alertBox({ type: 'success', title: 'Dữ liệu đã được nhập', onClose: reload,
                    text: 'Đã thêm ' + thousand(r.result.inserted) + ' · cập nhật ' + thousand(r.result.updated) + ' · bỏ qua ' + thousand(r.result.skipped) + ' dòng.' });
                });
                return false;
              } }] : [{ label: 'Đóng', kind: 'ghost' }]
            });
          });
        }
      };
      form(o);
    },

    'model-run': function (el) {
      var label = (el && el.dataset && el.dataset.store) || ($('#run-store') || {}).value;
      withLoading({ title: 'Đang chạy dự báo · Quản trị', text: label }, post('/api/admin/forecast/run/', { store: storeCode(label) }), function (res) {
        if (res.ok) {
          return info({ title: 'Dự báo cửa hàng đã hoàn tất', onClose: reload,
            rows: [['Cửa hàng', res.store_name], ['Ngày dự báo', res.plan.service_date.split('-').reverse().join('/')], ['Phạm vi', res.plan.lines + ' món']],
            note: storeCode(label) + ' · ' + res.plan.lines + ' món · Tổng dự báo ' + thousand(res.plan.forecast_total) + ' phần · ' + (res.plan.status === 'approved' ? 'Đã gửi bếp' : 'Chờ duyệt') });
        }
        alertBox({ type: 'error', title: res.error === 'approved' ? 'Đã duyệt – không chạy lại dự báo' : 'Không thể chạy dự báo', text: res.message });
      });
    },
    'model-run-all': function () {
      var n = ((window.QSR_DATA || {}).stores || []).length;
      info({
        title: 'Chạy dự báo cho tất cả cửa hàng',
        rows: [['Phạm vi', n + ' cửa hàng · ' + n * 50 + ' món'], ['Ngày dự báo', 'Ngày phục vụ kế tiếp']],
        note: 'Kết quả dự báo được cập nhật; danh sách bếp đang thực hiện được giữ đến lần duyệt mới. Cửa hàng chưa kiểm kho hoặc đã duyệt sẽ được bỏ qua.',
        actions: [{ label: 'Hủy', kind: 'ghost' }, { label: 'Chạy dự báo', kind: 'primary', run: function () {
          withLoading({ title: 'Đang chạy dự báo · Toàn hệ thống', text: 'Phạm vi: ' + n + ' cửa hàng · có thể mất vài phút.' }, post('/api/admin/forecast/run-all/'), function (res) {
            if (!res.ok) return failBox(res, 'Không thể chạy dự báo');
            var skipped = Object.keys(res.skipped);
            info({ title: 'Dự báo toàn hệ thống đã hoàn tất', onClose: reload,
              rows: [['Đã chạy', res.done.length + ' cửa hàng'], ['Bỏ qua', skipped.length + ' cửa hàng']],
              note: skipped.length ? skipped.map(function (k) { return k + ': ' + ({ approved: 'đã duyệt', no_inventory: 'chưa kiểm kho', no_data: 'thiếu dữ liệu' }[res.skipped[k]] || res.skipped[k]); }).join(' · ') : '' });
          });
          return false;
        } }]
      });
    },

    'store-form': function (el) {
      var d = el ? el.dataset : {}, edit = !!d.code;
      var o = {
        title: edit ? 'Sửa cửa hàng' : 'Thêm cửa hàng', submit: edit ? 'Lưu thay đổi' : 'Lưu cửa hàng',
        values: { code: d.code || '', name: d.name || '', city: d.city || '', manager: d.manager || 'Chưa gán' },
        fields: [{ name: 'code', label: 'Mã cửa hàng', readonly: edit }, { name: 'name', label: 'Tên cửa hàng' },
          { name: 'city', label: 'Thành phố', placeholder: 'Chicago, IL' }].concat(edit ? [{ name: 'manager', label: 'Quản lý phụ trách', type: 'select', pick: 'manager' }] : []),
        onSubmit: function (v) {
          var body = { code: v.code, name: v.name, city: v.city, creating: !edit }; if (edit) body.manager = v.manager;
          withLoading({ title: 'Đang lưu cửa hàng', text: 'Vui lòng đợi.' }, post('/api/admin/stores/save/', body), function (res) {
            if (!res.ok) return alertBox({ type: 'error', title: 'Chưa thể lưu cửa hàng', text: res.message, onClose: function () { form(o, v); } });
            alertBox({ type: 'success', title: 'Thông tin cửa hàng đã được lưu', onClose: reload,
              text: 'Trạng thái: Đã lưu · ' + WHO + (res.replaced ? ' · Quản lý ' + res.replaced + ' chuyển sang chưa gán' : '') });
          });
        }
      };
      form(o);
    },

    'acct-form': function (el) {
      var d = el ? el.dataset : {}, edit = !!d.user;
      var o = {
        title: edit ? 'Sửa tài khoản' : 'Thêm tài khoản', submit: 'Lưu tài khoản',
        values: { name: d.name || '', user: d.user || '', role: d.role || 'Quản lý cửa hàng', scope: d.scope || '' },
        fields: [{ name: 'name', label: 'Tên hiển thị' }, { name: 'user', label: 'Tên đăng nhập' },
          { name: 'role', label: 'Vai trò', type: 'select', pick: 'role' }, { name: 'scope', label: 'Phạm vi', type: 'select', pick: 'scope', placeholder: 'Chọn phạm vi' }],
        extra: edit ? '<button type="button" id="pw-reset" class="h-9 px-4 rounded-lg border border-ink/20 text-sm">Cấp lại mật khẩu</button>' : '',
        afterOpen: function (card) {
          var b = $('#pw-reset', card);
          if (b) b.onclick = function () {
            alertBox({ type: 'warning', title: 'Cấp lại mật khẩu?', text: 'Hệ thống tạo mật khẩu tạm cho ' + d.user + ' và hiển thị một lần.',
              actions: [{ label: 'Hủy', kind: 'ghost' }, { label: 'Cấp lại', kind: 'primary', run: function () {
                withLoading({ title: 'Đang cấp lại mật khẩu', text: 'Vui lòng đợi.' }, post('/api/admin/accounts/reset-password/', { username: d.user }), function (res) {
                  if (res.ok) alertBox({ type: 'success', title: 'Đã cấp lại mật khẩu', text: 'Mật khẩu tạm của ' + res.username + ': ' + res.temp_password + ' (chỉ hiển thị một lần)' });
                  else failBox(res, 'Không thể cấp lại mật khẩu');
                });
                return false;
              } }] });
          };
        },
        onSubmit: function (v) {
          var body = { original: d.user || '', name: v.name, username: v.user, role: v.role, scope: v.scope };
          withLoading({ title: 'Đang lưu tài khoản', text: 'Vui lòng đợi.' }, post('/api/admin/accounts/save/', body), function (res) {
            if (!res.ok) return alertBox({ type: 'error', title: 'Chưa thể lưu tài khoản', text: res.message, onClose: function () { form(o, v); } });
            alertBox({ type: 'success', title: 'Tài khoản đã được cập nhật', onClose: reload,
              text: 'Trạng thái: Đã lưu · ' + WHO + (res.temp_password ? ' · Mật khẩu tạm: ' + res.temp_password + ' (chỉ hiển thị một lần)' : '') });
          });
        }
      };
      form(o);
    },
    'acct-disable': function (el) {
      var user = el.getAttribute('data-user');
      alertBox({
        type: 'warning', title: 'Vô hiệu hóa tài khoản?', width: 'max-w-[480px]',
        text: 'Tài khoản ' + user + ' chuyển sang Ngừng hoạt động và không thể đăng nhập. Lịch sử duyệt và kiểm kho vẫn được giữ.',
        actions: [{ label: 'Hủy', kind: 'ghost' }, { label: 'Vô hiệu hóa', kind: 'danger', run: function () {
          withLoading({ title: 'Đang cập nhật tài khoản', text: 'Vui lòng đợi.' }, post('/api/admin/accounts/disable/', { username: user }), function (res) {
            if (res.ok) alertBox({ type: 'success', title: 'Tài khoản đã được cập nhật', text: 'Trạng thái: Đã lưu · ' + WHO, onClose: reload });
            else failBox(res, 'Không thể vô hiệu hóa');
          });
          return false;
        } }]
      });
    },

    'cfg-save': function () {
      var body = {};
      $$('[data-cfg]').forEach(function (e) { body[e.getAttribute('data-cfg')] = e.type === 'checkbox' ? e.checked : e.value; });
      withLoading({ title: 'Đang lưu cấu hình', text: 'Vui lòng đợi.' }, post('/api/admin/config/save/', body), function (res) {
        if (res.ok) info({ title: 'Cấu hình đã được lưu', rows: [['Trạng thái', 'Đã lưu'], ['Người thực hiện', WHO], ['Thời điểm', res.at]] });
        else failBox(res, 'Chưa thể lưu cấu hình');
      });
    }
  };

  Object.keys(LIVE_ACTIONS).forEach(function (k) { ACTIONS[k] = LIVE_ACTIONS[k]; });
  Object.keys(ADMIN_ACTIONS).forEach(function (k) { ACTIONS[k] = ADMIN_ACTIONS[k]; });

  function goHandler(e) {
    var b = e.target.closest('[data-go]');
    if (b) go(b.getAttribute('data-go'));
  }

  /* ---------- gắn sự kiện toàn trang ---------- */
  document.addEventListener('click', function (e) {
    var cal = e.target.closest('[data-calendar]');
    if (cal && !current) {
      e.preventDefault();
      var kind = cal.getAttribute('data-calendar');
      if (kind === 'range') {
        return rangeCalendar({ value: cal.value, onApply: function (v) { cal.value = v; } });
      }
      return calendar({
        title: kind === 'inventory' ? 'Chọn ngày kiểm kho' : 'Chọn ngày phục vụ',
        selected: cal.value, onApply: function (v) {
          cal.value = v; cal.dispatchEvent(new Event('change'));
          if (cal.hasAttribute('data-autosubmit') && cal.form) cal.form.submit();
        }
      });
    }
    var el = e.target.closest('[data-act]');
    if (!el || el.tagName === 'FORM') return;
    var fn = ACTIONS[el.getAttribute('data-act')];
    if (fn) { e.preventDefault(); fn(el, e); }
  });

  document.addEventListener('submit', function (e) {
    var f = e.target.closest('[data-submit]');
    if (!f) return;
    e.preventDefault();
    ACTIONS[f.getAttribute('data-submit')](f, e);
  });

  /* <select data-choice="key"> mở popup chọn thay cho dropdown gốc. */
  function interceptSelect(e) {
    var s = e.target.closest && e.target.closest('select[data-choice]');
    if (!s) return;
    if (e.type === 'keydown' && [' ', 'Enter', 'ArrowDown'].indexOf(e.key) < 0) return;
    e.preventDefault();
    s.blur();
    var ch = CHOICES[s.getAttribute('data-choice')];
    if (!ch) return;
    choice({
      title: ch.title, hint: ch.hint, options: ch.options,
      onPick: function (v) {
        var setVal = function (val) {
          var opt = Array.prototype.find.call(s.options, function (o) { return o.value === val || o.text.indexOf(val) === 0; });
          if (!opt) { opt = new Option(val, val); s.add(opt); }
          s.value = opt.value;
          s.dispatchEvent(new Event('change'));
        };
        /* "Khác" yêu cầu nhập lý do cụ thể trước khi áp dụng. */
        if (s.getAttribute('data-choice') === 'reason' && v === 'Khác') ACTIONS['other-reason'](setVal);
        else setVal(v);
      }
    });
  }
  document.addEventListener('change', function (e) {
    var t = e.target.closest && e.target.closest('[data-pref]');
    if (!t) return;
    var body = {}; body[t.getAttribute('data-pref')] = t.checked;
    post(API.prefs, body).then(function (res) { if (!res.ok) { t.checked = !t.checked; failBox(res, 'Không lưu được tùy chọn'); } });
  });
  document.addEventListener('mousedown', interceptSelect);
  document.addEventListener('keydown', interceptSelect);

  window.QSR = { open: open, close: close, alert: alertBox, loading: loading, info: info, choice: choice, form: form, flow: flow };
})();
