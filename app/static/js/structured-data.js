var script = document.createElement('script');
script.type = 'application/ld+json';
script.text = JSON.stringify({
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "JudgeAccount",
    "url": "https://judgeaccount.com",
    "description": "A public platform dedicated to documenting judicial conduct through firsthand experiences and verified media sources."
});
document.head.appendChild(script);
