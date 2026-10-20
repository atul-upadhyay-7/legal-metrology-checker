(function(){
  var b=document.getElementById('burger'),m=document.getElementById('menu');
  if(b&&m){b.addEventListener('click',function(){var o=m.classList.toggle('open');b.setAttribute('aria-expanded',o?'true':'false')})}
  if(window.Motion)Motion.scrollRise();
})();
