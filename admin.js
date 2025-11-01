let currentAdmin = null
let activeChatIndex = null

function loginAdmin() {
  let u = document.getElementById('adminUser').value
  let p = document.getElementById('adminPass').value
  let users = JSON.parse(localStorage.getItem('users')||'{}')
  if(users[u] && users[u].password===p && users[u].admin) {
    currentAdmin = u
    document.getElementById('authAdmin').style.display='none'
    document.getElementById('adminMain').style.display='block'
    loadAdminAnnouncements()
    loadContacts()
  } else alert('Admin girişi başarısız')
}

function showAdminTab(tab) {
  document.querySelectorAll('.adminTab').forEach(t=>t.style.display='none')
  document.getElementById(tab).style.display='block'
}

function addAdminAnnouncement(section) {
  let msg = prompt('Duyuru yazın')
  if(!msg) return
  let anns = JSON.parse(localStorage.getItem('announcements')||'{}')
  if(!anns[section]) anns[section]=[]
  anns[section].push(msg)
  localStorage.setItem('announcements', JSON.stringify(anns))
  loadAdminAnnouncements()
}

function loadAdminAnnouncements() {
  let anns = JSON.parse(localStorage.getItem('announcements')||'{}')
  let el = document.getElementById('adminAnnList')
  el.innerHTML=''
  ['dev','news','general'].forEach(sec=>{
    if(anns[sec]) anns[sec].forEach(a=> el.innerHTML += sec.toUpperCase()+' - '+a+'<br>')
  })
}

function loadContacts() {
  let contacts = JSON.parse(localStorage.getItem('contacts')||'[]')
  let el = document.getElementById('contactList')
  el.innerHTML=''
  contacts.forEach((c,i)=>{
    el.innerHTML += '<div>'+c.name+' - '+c.reason+' <button onclick="openAdminChat('+i+')">Sohbet Et</button></div>'
  })
}

function openAdminChat(index) {
  activeChatIndex = index
  document.getElementById('adminChat').style.display='block'
  loadAdminChat()
}

function loadAdminChat() {
  if(activeChatIndex===null) return
  let contacts = JSON.parse(localStorage.getItem('contacts')||'[]')
  let chatEl = document.getElementById('chatBox')
  chatEl.innerHTML=''
  contacts[activeChatIndex].messages.forEach(m=>{
    chatEl.innerHTML += m.from + ': ' + m.text + '<br>'
  })
}

function sendAdminMessage() {
  if(activeChatIndex===null) return
  let msg = document.getElementById('chatInputAdmin').value
  if(!msg) return
  let contacts = JSON.parse(localStorage.getItem('contacts')||'[]')
  contacts[activeChatIndex].messages.push({from:currentAdmin, text:msg})
  localStorage.setItem('contacts', JSON.stringify(contacts))
  loadAdminChat()
  document.getElementById('chatInputAdmin').value=''
}
