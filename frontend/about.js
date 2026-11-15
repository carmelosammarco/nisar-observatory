/* One local player, including an expanded dialog for embedded browsers. */
(()=>{
  const video=document.getElementById('about-introduction-video');
  const slot=document.getElementById('about-video-slot');
  const dialog=document.getElementById('about-video-dialog');
  const stage=document.getElementById('about-video-stage');
  const expand=document.getElementById('about-video-expand');
  const close=document.getElementById('about-video-close');
  if(!video||!slot||!dialog||!stage||!expand||!close)return;
  expand.addEventListener('click',()=>{
    const playing=!video.paused;
    video.pause();dialog.showModal();stage.append(video);
    if(playing)video.play().catch(()=>{});
  });
  close.addEventListener('click',()=>dialog.close());
  dialog.addEventListener('close',()=>{
    video.pause();
    if(!slot.contains(video))slot.append(video);
    if(document.getElementById('about')?.classList.contains('active')){
      slot.scrollIntoView({block:'center',behavior:'instant'});
      expand.focus({preventScroll:true});
    }
  });
})();
