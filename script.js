let currentUser = null;

function signup() {
  let u = document.getElementById('username').value
  let n = document.getElementById('nickname').value
  let p = document.getElementById('password').value
  if(!u || !p) { alert('Kullanıcı adı ve şifre gerekli'); return; }
  
  let users = JSON.parse(localStorage.getItem('users')||'{}')
  if(users[u]) { alert('Kullanıcı zaten var'); return; }
  
  // Admin tanımlaması: TFDholderr ve BaskaAdmin admin
  users[u] = {password:p, nickname:n, admin: (u==='TFDholderr' || u==='BaskaAdmin')}
  localStorage.setItem('users', JSON.stringify(users))
  alert('Kayıt başarılı')
}

function login() {
  let u = document.getElementById('username').value
  let p = document.getElementById('password').value
  let users = JSON.parse(localStorage.getItem('users')||'{}')
  if(users[u] && users[u].password===p) {
    currentUser = u
    document.getElementById('auth').style.display='none'
    document.getElementById('main').style.display='block'
    alert('Hoşgeldin ' + users[u].nickname)
    loadTabs()
  } else alert('Kullanıcı adı veya şifre yanlış')
}

// Çıkış yap fonksiyonu
function logout() {
  currentUser = null
  document.getElementById('main').style.display = 'none'
  document.getElementById('auth').style.display = 'block'
  alert('Çıkış yapıldı')
}

function showTab(tab) {
  document.querySelectorAll('.tab').forEach(t=>t.style.display='none')
  document.getElementById(tab).style.display='block'
}

// Duyuru ve chat fonksiyonları (öncekiler gibi)
function loadTabs() {
  let users = JSON.parse(localStorage.getItem('users')||'{}')
  if(users[currentUser].admin) {
    document.getElementById('dev').innerHTML += '<br><button onclick="addAnnouncement(\'dev\')">Duyuru Ekle</button>'
    document.getElementById('news').innerHTML += '<br><button onclick="addAnnouncement(\'news\')">Duyuru Ekle</button>'
    document.getElementById('general').innerHTML += '<br><button onclick="addAnnouncement(\'general\')">Duyuru Ekle</button>'
  }
  loadAnnouncements()
}

function addAnnouncement(section) {
  let msg = prompt('Duyuru yazın')
  if(!msg) return
  let anns = JSON.parse(localStorage.getItem('announcements')||'{}')
  if(!anns[section]) anns[section]=[]
  anns[section].push(msg)
  localStorage.setItem('announcements', JSON.stringify(anns))
  loadAnnouncements()
}

function loadAnnouncements() {
  let anns = JSON.parse(localStorage.getItem('announcements')||'{}')
  ['dev','news','general'].forEach(sec=>{
    let el = document.getElementById(sec)
    el.innerHTML = sec.toUpperCase() + '<br>'
    if(anns[sec]) anns[sec].forEach(a=> el.innerHTML += '- '+a+'<br>')
  })
}

// İletişim formu
function sendContact() {
  let name = document.getElementById('contactName').value
  let reason = document.getElementById('contactReason').value
  let image = document.getElementById('contactImage').value
  let contacts = JSON.parse(localStorage.getItem('contacts')||'[]')
  contacts.push({user:currentUser, name, reason, image, messages:[]})
  localStorage.setItem('contacts', JSON.stringify(contacts))
  alert('Destek gönderildi adminlere bildirim gitti')
}

// Basit chat
function openChat(contactIndex) {
  document.getElementById('chatWindow').style.display='block'
  loadChat(contactIndex)
}

function loadChat(index) {
  let contacts = JSON.parse(localStorage.getItem('contacts')||'[]')
  let chatEl = document.getElementById('chatMessages')
  chatEl.innerHTML=''
  contacts[index].messages.forEach(m=>{
    chatEl.innerHTML += m.from + ': ' + m.text + '<br>'
  })
}

function sendMessage() {
  let msg = document.getElementById('chatInput').value
  if(!msg) return
  let contacts = JSON.parse(localStorage.getItem('contacts')||'[]')
  contacts[0].messages.push({from:currentUser, text:msg})
  localStorage.setItem('contacts', JSON.stringify(contacts))
  loadChat(0)
  document.getElementById('chatInput').value=''
}
