document.addEventListener('DOMContentLoaded', () => {
    const data = window.SHOWCASE_DATA;
    if (!data) return;

    // --- Inject Data ---

    // 1. Hero Stats
    const statsGrid = document.getElementById('statsGrid');
    const heroStats = [
        { label: 'Commits', value: data.hero.commits },
        { label: 'Lines Added', value: data.hero.linesAdded },
        { label: 'Files', value: data.hero.filesModified },
        { label: 'Merged PRs', value: data.hero.mergedPRs },
        { label: 'Database Models', value: data.hero.databaseModels },
        { label: 'Repositories', value: data.hero.repositories }
    ];

    heroStats.forEach(stat => {
        const div = document.createElement('div');
        div.className = 'stat-card';
        div.innerHTML = `
            <div class="stat-number" data-target="${stat.value}">0</div>
            <div class="stat-label">${stat.label}</div>
        `;
        statsGrid.appendChild(div);
    });

    // 2. Timeline
    const timelineContainer = document.getElementById('timelineContainer');
    data.timeline.forEach(item => {
        const div = document.createElement('div');
        div.className = 'timeline-item';
        div.innerHTML = `
            <div class="timeline-dot"></div>
            <div class="timeline-content">
                <div class="timeline-date">${item.date}</div>
                <h4>${item.title}</h4>
                <p style="font-size: 0.85rem; color: #9ca3af;">Commit: ${item.hash} | ${item.files} files | ${item.lines} lines added</p>
            </div>
        `;
        timelineContainer.appendChild(div);
    });

    // 3. Top Achievements
    const milestonesGrid = document.getElementById('milestonesGrid');
    data.topCommits.slice(0, 6).forEach(commit => {
        const div = document.createElement('div');
        div.className = 'milestone-card';
        div.innerHTML = `
            <div class="milestone-title">${commit.title}</div>
            <div class="milestone-stats">
                <span>📅 ${commit.date}</span>
                <span>📄 ${commit.files_changed} Files</span>
                <span>➕ ${commit.lines_changed} Lines</span>
            </div>
            <a href="#" class="btn-open">Open &rarr;</a>
        `;
        milestonesGrid.appendChild(div);
    });


    // --- Animations & Intersection Observer ---

    const observerOptions = {
        threshold: 0.1,
        rootMargin: "0px 0px -50px 0px"
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('show');
                
                // Trigger counter animation if it's the hero section
                if (entry.target.id === 'hero') {
                    animateCounters();
                }
                
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.hidden').forEach(el => observer.observe(el));

    // Force first section to appear quickly
    setTimeout(() => {
        const hero = document.getElementById('hero');
        if (hero) hero.classList.add('show');
        animateCounters();
    }, 100);

    // Number Counter Animation
    let countersAnimated = false;
    function animateCounters() {
        if (countersAnimated) return;
        countersAnimated = true;
        
        const counters = document.querySelectorAll('.stat-number');
        counters.forEach(counter => {
            const target = +counter.getAttribute('data-target');
            const duration = 2000; // ms
            const increment = target / (duration / 16); // 60fps
            
            let current = 0;
            const updateCounter = () => {
                current += increment;
                if (current < target) {
                    counter.innerText = Math.ceil(current).toLocaleString();
                    requestAnimationFrame(updateCounter);
                } else {
                    counter.innerText = target.toLocaleString();
                }
            };
            updateCounter();
        });
    }

    // --- Background Particles (Stars) ---
    const canvas = document.getElementById('particles');
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const particles = [];
    for (let i = 0; i < 100; i++) {
        particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            r: Math.random() * 2,
            dx: (Math.random() - 0.5) * 0.5,
            dy: (Math.random() - 0.5) * 0.5,
            alpha: Math.random()
        });
    }

    function drawParticles() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        particles.forEach(p => {
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 255, 255, ${p.alpha})`;
            ctx.fill();
            
            p.x += p.dx;
            p.y += p.dy;
            
            if (p.x < 0 || p.x > canvas.width) p.dx *= -1;
            if (p.y < 0 || p.y > canvas.height) p.dy *= -1;
        });
        requestAnimationFrame(drawParticles);
    }
    drawParticles();

    window.addEventListener('resize', () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    });

    // Initialize Mermaid
    if (window.mermaid) {
        mermaid.initialize({ startOnLoad: true, theme: 'dark', themeVariables: { fontFamily: 'Inter' } });
    }
});
