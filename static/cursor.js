// dot
const dot = document.createElement('div');
dot.className = 'cursor-dot';
document.body.appendChild(dot);

// Move dot 
document.addEventListener('mousemove', e => {
    dot.style.left = e.clientX + 'px';
    dot.style.top  = e.clientY + 'px';
});

// click
document.addEventListener('click', e => {
    const drop = document.createElement('div');
    drop.className = 'water-drop';
    drop.style.left = e.clientX + 'px';
    drop.style.top  = e.clientY + 'px';
    document.body.appendChild(drop);
    //animation ends
    drop.addEventListener('animationend', () => drop.remove());
});

// mousemove
document.addEventListener('mousemove', e => {
    const trail = document.createElement('div');
    trail.className = 'cursor-trail';
    trail.style.left = e.clientX + 'px';
    trail.style.top  = e.clientY + 'px';
    document.body.appendChild(trail);
    trail.addEventListener('animationend', () => trail.remove());
});
