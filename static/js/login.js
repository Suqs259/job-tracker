const $ = (id) => document.getElementById(id);

const state = { mode: 'login' };

async function init() {
  try {
    const response = await fetch('/api/auth/status');
    const status = await response.json();
    if (status.logged_in) {
      window.location.href = '/';
      return;
    }
    state.mode = status.initialized ? 'login' : 'register';
  } catch (error) {
    state.mode = 'login';
  }

  const isRegister = state.mode === 'register';
  $('auth-subtitle').textContent = isRegister
    ? '首次使用，请设置一个账号（注册后入口自动关闭）'
    : '请登录后继续';
  $('auth-submit').textContent = isRegister ? '创建账号并进入' : '登录';
  $('auth-password').autocomplete = isRegister ? 'new-password' : 'current-password';
  $('auth-form').hidden = false;
  $('auth-username').focus();
}

async function submit(event) {
  event.preventDefault();
  const button = $('auth-submit');
  const errorBox = $('auth-error');
  errorBox.hidden = true;
  button.disabled = true;
  button.textContent = state.mode === 'register' ? '创建中...' : '登录中...';

  try {
    const response = await fetch(`/api/auth/${state.mode}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: $('auth-username').value.trim(),
        password: $('auth-password').value,
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `请求失败（${response.status}）`);
    window.location.href = '/';
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.hidden = false;
    button.disabled = false;
    button.textContent = state.mode === 'register' ? '创建账号并进入' : '登录';
  }
}

$('auth-form').addEventListener('submit', submit);
init();
