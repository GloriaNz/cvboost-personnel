/* ============================================================
   CVBoost — main.js  |  Rich Interactions & Animations
   ============================================================ */

// ── 1. Navbar: shadow on scroll + mobile toggle ─────────────
(function initNav() {
  const navbar    = document.getElementById('navbar');
  const toggle    = document.getElementById('navToggle');
  const navLinks  = document.getElementById('navLinks');

  // Scroll shadow
  window.addEventListener('scroll', () => {
    if (navbar) navbar.classList.toggle('scrolled', window.scrollY > 10);
  }, { passive: true });

  // Mobile toggle
  if (toggle && navLinks) {
    toggle.addEventListener('click', () => {
      const open = navLinks.classList.toggle('open');
      toggle.classList.toggle('open', open);
      toggle.setAttribute('aria-expanded', open);
    });
    // Close on outside click
    document.addEventListener('click', (e) => {
      if (!toggle.contains(e.target) && !navLinks.contains(e.target)) {
        navLinks.classList.remove('open');
        toggle.classList.remove('open');
      }
    });
  }
})();

// ── 2. Flash messages: auto-dismiss ────────────────────────
(function initFlash() {
  document.querySelectorAll('.flash').forEach(el => {
    // Auto-remove after 4s
    const timer = setTimeout(() => dismissFlash(el), 4200);
    el.querySelector('.flash-close')?.addEventListener('click', () => {
      clearTimeout(timer);
      dismissFlash(el);
    });
  });
  function dismissFlash(el) {
    el.classList.add('flash-hiding');
    el.addEventListener('transitionend', () => el.remove(), { once: true });
  }
})();

// ── 3. Ripple effect on buttons ─────────────────────────────
(function initRipple() {
  document.querySelectorAll('.btn-ripple').forEach(btn => {
    btn.addEventListener('click', function(e) {
      const rect    = this.getBoundingClientRect();
      const size    = Math.max(rect.width, rect.height) * 2;
      const x       = e.clientX - rect.left - size / 2;
      const y       = e.clientY - rect.top  - size / 2;
      const ripple  = document.createElement('span');
      ripple.className = 'ripple';
      Object.assign(ripple.style, {
        width: size + 'px', height: size + 'px',
        left:  x    + 'px', top:   y    + 'px',
      });
      this.appendChild(ripple);
      ripple.addEventListener('animationend', () => ripple.remove());
    });
  });
})();

// ── 4. Scroll-reveal via IntersectionObserver ────────────────
(function initReveal() {
  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  document.querySelectorAll('.reveal, .reveal-right').forEach((el, i) => {
    const delay = parseFloat(getComputedStyle(el).getPropertyValue('--d') || 0);
    el.style.transitionDelay = delay + 's';
    io.observe(el);
  });
})();

// ── 5. Hero: particle system ─────────────────────────────────
(function initParticles() {
  const container = document.getElementById('particles');
  if (!container) return;

  function make() {
    const p = document.createElement('div');
    p.className = 'hero-particle';
    const size = Math.random() * 3 + 1.5;
    const dur  = Math.random() * 18 + 10;
    const left = Math.random() * 100;
    Object.assign(p.style, {
      width:  size + 'px', height: size + 'px',
      left: left + '%',
      animationDuration: dur + 's',
      animationDelay: (Math.random() * dur) + 's',
      opacity: (Math.random() * 0.5 + 0.2).toFixed(2),
    });
    container.appendChild(p);
    p.addEventListener('animationend', () => p.remove());
  }
  // Initial burst
  for (let i = 0; i < 28; i++) make();
  // Continuous spawn
  setInterval(make, 900);
})();

// ── 6. Typing effect on hero ─────────────────────────────────
(function initTyping() {
  const el = document.getElementById('typedText');
  if (!el) return;
  const words   = ['carrière grâce à l\'IA.', 'CV en 2 minutes.', 'profil avec l\'IA.', 'candidature idéale.'];
  let wi = 0, ci = 0, deleting = false;

  function tick() {
    const word = words[wi];
    if (!deleting) {
      ci++;
      el.textContent = word.slice(0, ci);
      if (ci === word.length) { deleting = true; setTimeout(tick, 2200); return; }
      setTimeout(tick, 55 + Math.random() * 30);
    } else {
      ci--;
      el.textContent = word.slice(0, ci);
      if (ci === 0) { deleting = false; wi = (wi + 1) % words.length; setTimeout(tick, 400); return; }
      setTimeout(tick, 32);
    }
  }
  tick();
})();

// ── 7. Animated counters ─────────────────────────────────────
(function initCounters() {
  const io = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.querySelectorAll('.stat-val[data-target]').forEach(el => {
        const target = +el.dataset.target;
        const dur    = 1600;
        const start  = performance.now();
        function frame(now) {
          const p = Math.min((now - start) / dur, 1);
          el.textContent = Math.floor(easeOut(p) * target);
          if (p < 1) requestAnimationFrame(frame);
          else el.textContent = target;
        }
        requestAnimationFrame(frame);
      });
      io.unobserve(entry.target);
    });
  }, { threshold: 0.5 });

  const statsEl = document.querySelector('.hero-stats');
  if (statsEl) io.observe(statsEl);

  function easeOut(t) { return 1 - Math.pow(1 - t, 3); }
})();

// ── 8. Password toggle ────────────────────────────────────────
(function initPwdToggle() {
  document.querySelectorAll('.pwd-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const input = document.getElementById(btn.dataset.target);
      if (!input) return;
      const isText = input.type === 'text';
      input.type = isText ? 'password' : 'text';
      // Swap eye icon
      btn.innerHTML = isText
        ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`
        : `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;
    });
  });
})();

// ── 9. Password strength meter ────────────────────────────────
(function initStrength() {
  const pwdField = document.getElementById('register-password') || document.querySelector('input[type="password"]');
  const bars     = document.querySelectorAll('.strength-bar');
  const label    = document.querySelector('.strength-label');
  if (!pwdField || !bars.length) return;

  pwdField.addEventListener('input', () => {
    const v = pwdField.value;
    let score = 0;
    if (v.length >= 8)                score++;
    if (/[A-Z]/.test(v))              score++;
    if (/[^a-zA-Z0-9]/.test(v))      score++;
    const labels = ['', 'Faible', 'Moyen', 'Fort'];
    bars.forEach((b, i) => {
      b.className = 'strength-bar';
      if (i < score) b.classList.add(`active-${score}`);
    });
    if (label) label.textContent = labels[score] || '';
  });
})();

// ── 10. Drag & drop upload ────────────────────────────────────
(function initDrop() {
  const zone     = document.getElementById('dropZone');
  const fileInput= document.getElementById('cv-file-input');
  const preview  = document.getElementById('dzPreview');
  const nameEl   = document.getElementById('dzName');
  const sizeEl   = document.getElementById('dzSize');
  const removeBtn= document.getElementById('dzRemove');
  const submitBtn= document.getElementById('upload-submit');
  const dzContent= document.getElementById('dzContent');
  if (!zone || !fileInput) return;
  const maxSize = 5 * 1024 * 1024;

  function fmtSize(b) {
    if (b < 1024) return b + ' o';
    if (b < 1048576) return (b/1024).toFixed(1) + ' Ko';
    return (b/1048576).toFixed(1) + ' Mo';
  }

  function showPreview(file) {
    if (!file.name.match(/\.(pdf|docx)$/i)) {
      showToast('Type de fichier invalide. PDF ou DOCX uniquement.', 'error');
      clearPreview();
      return;
    }
    if (file.size > maxSize) {
      showToast('Le fichier ne doit pas dépasser 5 Mo.', 'error');
      clearPreview();
      return;
    }
    if (nameEl) nameEl.textContent = file.name;
    if (sizeEl) sizeEl.textContent = fmtSize(file.size);
    if (preview)  preview.style.display  = 'flex';
    if (dzContent)dzContent.style.display = 'none';
    if (submitBtn) { submitBtn.disabled = false; submitBtn.classList.remove('btn-disabled'); }
  }

  function clearPreview() {
    if (preview)  preview.style.display  = 'none';
    if (dzContent)dzContent.style.display = 'block';
    fileInput.value = '';
    if (submitBtn) submitBtn.disabled = true;
  }

  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) showPreview(fileInput.files[0]);
  });
  if (removeBtn) removeBtn.addEventListener('click', (e) => { e.stopPropagation(); clearPreview(); });

  zone.addEventListener('dragover',  (e) => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', ()  => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault(); zone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (!file) return;
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    showPreview(file);
  });
})();

// ── 11. Form live validation ──────────────────────────────────
(function initValidation() {
  // Email check
  document.querySelectorAll('input[type="email"]').forEach(el => {
    el.addEventListener('blur', () => {
      const valid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(el.value);
      el.classList.toggle('is-valid',   el.value.length > 0 && valid);
      el.classList.toggle('is-invalid', el.value.length > 0 && !valid);
    });
  });
  // Confirm password
  const pw1 = document.getElementById('register-password');
  const pw2 = document.getElementById('register-confirm');
  if (pw1 && pw2) {
    pw2.addEventListener('input', () => {
      if (!pw2.value) return;
      const match = pw1.value === pw2.value;
      pw2.classList.toggle('is-valid',   match);
      pw2.classList.toggle('is-invalid', !match);
    });
  }
})();

// ── 13. Toast helper ─────────────────────────────────────────
function showToast(msg, type = 'info') {
  const container = document.getElementById('flashContainer') || (() => {
    const c = document.createElement('div');
    c.id = 'flashContainer';
    c.className = 'flash-container';
    document.body.appendChild(c);
    return c;
  })();
  const toast = document.createElement('div');
  const cls   = type === 'error' ? 'danger' : type;
  toast.className = `flash flash-${cls}`;
  toast.innerHTML = `<span class="flash-icon"></span><span>${msg}</span><button class="flash-close" aria-label="Fermer"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>`;
  container.appendChild(toast);
  toast.querySelector('.flash-close').addEventListener('click', () => {
    toast.classList.add('flash-hiding');
    toast.addEventListener('transitionend', () => toast.remove(), { once: true });
  });
  setTimeout(() => {
    toast.classList.add('flash-hiding');
    toast.addEventListener('transitionend', () => toast.remove(), { once: true });
  }, 4500);
}

// ── 14. Animate history cards stagger ────────────────────────
(function initHistoryStagger() {
  document.querySelectorAll('.hist-card').forEach((card, i) => {
    card.style.animationDelay = (i * 0.07) + 's';
  });
})();

// ── 15. Interview answer character counter ───────────────────
(function initInterviewAnswerCounter() {
  const answer = document.getElementById('interview-answer');
  const counter = document.querySelector('[data-answer-length]');
  if (!answer || !counter) return;

  const updateCount = () => {
    counter.textContent = answer.value.length.toLocaleString('fr-FR');
  };
  answer.addEventListener('input', updateCount);
  updateCount();
})();

// ── 16. Interview audio ───────────────────────────────────────
(function initInterviewAudio() {
  document.querySelectorAll('.audio-controls').forEach(controls => {
    const form = controls.closest('form');
    const answer = form?.querySelector('textarea[name="answer"]');
    const recordButton = controls.querySelector('[data-audio-record]');
    const stopButton = controls.querySelector('[data-audio-stop]');
    const transcribeButton = controls.querySelector('[data-audio-transcribe]');
    const status = controls.querySelector('[data-audio-status]');
    if (!form || !answer || !recordButton || !stopButton || !transcribeButton || !status) return;

    let recorder;
    let stream;
    let chunks = [];
    let recording;
    let recordingTimer;
    let audioBlob;

    function setStatus(message, state = '') {
      status.textContent = message;
      status.dataset.state = state;
    }

    recordButton.addEventListener('click', async () => {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
        setStatus('L’enregistrement audio n’est pas pris en charge par ce navigateur.', 'error');
        return;
      }
    // Mode Temps Réel : Web Speech Recognition (Google Chrome / Edge / Safari)
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let liveRecognition;

    if (SpeechRecognition) {
      liveRecognition = new SpeechRecognition();
      liveRecognition.lang = 'fr-FR';
      liveRecognition.continuous = true;
      liveRecognition.interimResults = true;

      liveRecognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript + ' ';
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }
        if (finalTranscript) {
          answer.value = (answer.value + ' ' + finalTranscript).trim();
        }
        setStatus(interimTranscript ? `🗣️ En direct : "${interimTranscript}"` : 'Enregistrement en direct en cours…');
      };

      liveRecognition.onerror = (e) => {
        console.warn('Live SpeechRecognition error:', e.error);
      };
    }

    recordButton.addEventListener('click', async () => {
      audioBlob = undefined;
      chunks = [];
      recordButton.disabled = true;
      setStatus('Démarrage du microphone…');
      try {
        if (liveRecognition) {
          try { liveRecognition.start(); } catch (_) {}
        }
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mimeType = [
          'audio/webm;codecs=opus',
          'audio/webm',
          'audio/mp4',
        ].find(type => MediaRecorder.isTypeSupported(type));
        recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
        chunks = [];
        recorder.addEventListener('dataavailable', event => {
          if (event.data.size) chunks.push(event.data);
        });
        recorder.addEventListener('stop', () => {
          if (liveRecognition) {
            try { liveRecognition.stop(); } catch (_) {}
          }
          stream.getTracks().forEach(track => track.stop());
          stream = undefined;
          recording = undefined;
          audioBlob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });
          stopButton.disabled = true;
          recordButton.disabled = false;
          const withinLimit = audioBlob.size <= 5 * 1024 * 1024;
          transcribeButton.disabled = !audioBlob.size || !withinLimit;
          setStatus(
            answer.value.trim() 
              ? 'Réponse captée en temps réel ! Vous pouvez l’envoyer ou utiliser Transcrire (Groq Whisper) pour peaufiner.'
              : 'Enregistrement audio terminé. Cliquez sur Transcrire pour convertir avec Groq.'
          );
        });
        recorder.start();
        recording = setTimeout(() => recorder?.state === 'recording' && recorder.stop(), 60000);
        stopButton.disabled = false;
        transcribeButton.disabled = true;
        setStatus('🎙️ Parlez maintenant, votre voix est retranscrite en direct…');
      } catch (error) {
        if (stream) stream.getTracks().forEach(track => track.stop());
        stream = undefined;
        recordButton.disabled = false;
        setStatus('Impossible d’accéder au microphone. Vérifiez les autorisations du navigateur.', 'error');
        console.error('Microphone unavailable:', error);
      }
    });

    stopButton.addEventListener('click', () => {
      if (recording) clearTimeout(recording);
      recording = undefined;
      if (recorder?.state === 'recording') recorder.stop();
    });

    transcribeButton.addEventListener('click', async () => {
      if (!audioBlob) return;
      transcribeButton.disabled = true;
      setStatus('Transcription en cours. L’audio est transmis à Groq…');
      const extension = audioBlob.type.includes('mp4') ? 'mp4' : 'webm';
      const payload = new FormData();
      payload.append('audio', audioBlob, `interview.${extension}`);
      const csrfToken = form.querySelector('input[name="csrf_token"]');
      if (csrfToken) payload.append('csrf_token', csrfToken.value);
      try {
        const response = await fetch(controls.dataset.transcribeUrl, {
          method: 'POST',
          body: payload,
          headers: { Accept: 'application/json' },
        });
        const result = await response.json();
        if (!response.ok) {
          setStatus(result.error || 'La transcription a échoué. Réessayez.', 'error');
          transcribeButton.disabled = false;
          return;
        }
        answer.value = result.transcript;
        answer.focus();
        setStatus('Transcription prête. Relisez et corrigez le texte, puis envoyez votre réponse.');
      } catch (error) {
        setStatus('Impossible de joindre le service de transcription. Réessayez.', 'error');
        transcribeButton.disabled = false;
        console.error('Audio transcription failed:', error);
      }
    });
  });

  let activeButton;
  let activeUtterance;

  function getFrenchVoice() {
    if (!window.speechSynthesis) return null;
    const voices = window.speechSynthesis.getVoices() || [];
    return voices.find(v => v.lang && (v.lang.startsWith('fr') || v.lang === 'fr-FR')) || voices[0] || null;
  }

  // Pre-load voices for Chrome/Edge
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = () => getFrenchVoice();
  }

  document.querySelectorAll('.audio-play-button').forEach(button => {
    button.addEventListener('click', () => {
      if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) {
        showToast('La synthèse vocale n’est pas prise en charge par ce navigateur.', 'error');
        return;
      }

      window.speechSynthesis.cancel();
      if (activeButton) {
        activeButton.disabled = false;
        activeButton.textContent = 'Écouter la question';
      }

      const rawText = button.dataset.question || button.closest('article')?.querySelector('.interview-question-text')?.textContent || '';
      const textToSpeak = rawText.trim() || 'Bonjour, bienvenue à cet entretien. Pour commencer, parlez-moi de vous et de votre parcours.';

      const utterance = new window.SpeechSynthesisUtterance(textToSpeak);
      utterance.lang = 'fr-FR';
      utterance.rate = 0.95; // Rythme posé et naturel
      utterance.pitch = 1.0;

      const frVoice = getFrenchVoice();
      if (frVoice) {
        utterance.voice = frVoice;
      }

      activeButton = button;
      activeUtterance = utterance;
      button.disabled = true;
      button.textContent = '🔊 Lecture en cours…';

      const finish = () => {
        if (activeUtterance !== utterance) return;
        button.disabled = false;
        button.textContent = 'Écouter la question';
        activeButton = undefined;
        activeUtterance = undefined;
      };

      utterance.addEventListener('start', () => {
        window.dispatchEvent(new CustomEvent('speechSynthesisStart'));
      });

      utterance.addEventListener('end', () => {
        finish();
        window.dispatchEvent(new CustomEvent('speechSynthesisEnd'));
      });
      utterance.addEventListener('error', event => {
        finish();
        window.dispatchEvent(new CustomEvent('speechSynthesisEnd'));
        if (event.error !== 'canceled' && event.error !== 'interrupted') {
          showToast('La lecture audio a échoué.', 'error');
          console.error('Speech playback failed:', event.error);
        }
      });

      try {
        if (window.speechSynthesis.paused) {
          window.speechSynthesis.resume();
        }
        window.speechSynthesis.speak(utterance);
      } catch (error) {
        finish();
        window.dispatchEvent(new CustomEvent('speechSynthesisEnd'));
        showToast('La lecture audio a échoué.', 'error');
        console.error('Speech playback failed:', error);
      }
    });
  });
})();
