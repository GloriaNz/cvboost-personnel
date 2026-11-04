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
    const voiceStartButton = controls.querySelector('[data-voice-start]');
    const voicePauseButton = controls.querySelector('[data-voice-pause]');
    const voiceResumeButton = controls.querySelector('[data-voice-resume]');
    const voiceStopButton = controls.querySelector('[data-voice-stop]');
    const recordButton = controls.querySelector('[data-audio-record]');
    const stopButton = controls.querySelector('[data-audio-stop]');
    const transcribeButton = controls.querySelector('[data-audio-transcribe]');
    const status = controls.querySelector('[data-audio-status]');
    if (!form || !answer || !recordButton || !stopButton || !transcribeButton || !status) return;

    let recorder;
    let stream;
    let chunks = [];
    let recording;
    let audioBlob;
    let recordingRequestId = 0;

    function setStatus(message, state = '') {
      status.textContent = message;
      status.dataset.state = state;
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

    let voiceRecognition;
    let voiceMode = false;
    let voicePaused = false;
    let voiceSpeaking = false;
    let voiceSubmitting = false;
    let voiceTranscript = '';
    let silenceTimer;
    let listenRestartTimer;
    let voiceSessionId = 0;
    let introState = 'pending';
    let introPromise;

    function setVoiceStatus(message, state = '') {
      if (!status) return;
      status.textContent = message;
      status.dataset.state = state;
    }

    function setVoiceMode(active) {
      voiceMode = active;
      if (!active) voicePaused = false;
      updateVoiceControls();
      if (recordButton) recordButton.disabled = active;
      if (transcribeButton) transcribeButton.disabled = active || !audioBlob;
      const submitButton = form?.querySelector('[type="submit"]');
      if (submitButton) submitButton.disabled = active;
    }

    function updateVoiceControls() {
      const controlsActive = voiceMode || introState === 'playing' || voicePaused;
      if (voiceStartButton) voiceStartButton.hidden = controlsActive;
      if (voicePauseButton) voicePauseButton.hidden = !controlsActive || voicePaused;
      if (voiceResumeButton) voiceResumeButton.hidden = !controlsActive || !voicePaused;
      if (voiceStopButton) voiceStopButton.hidden = !controlsActive;
    }

    function startVoiceListening() {
      if (!voiceMode || voicePaused || !voiceRecognition || voiceSpeaking || voiceSubmitting) return;
      try {
        voiceRecognition.start();
        setVoiceStatus('Je vous écoute. Prenez votre temps.');
      } catch (error) {
        if (error.name === 'InvalidStateError') {
          clearTimeout(listenRestartTimer);
          listenRestartTimer = setTimeout(() => {
            if (voiceMode && !voicePaused && !voiceSpeaking && !voiceSubmitting) startVoiceListening();
          }, 350);
        } else {
          stopVoiceConversation();
          setVoiceStatus('Impossible de démarrer la reconnaissance vocale. Vérifiez les autorisations du microphone.', 'error');
          console.error('Interview speech recognition could not start:', error);
        }
      }
    }

    function pauseVoiceConversation() {
      if ((!voiceMode && introState !== 'playing') || voicePaused) return;
      voicePaused = true;
      clearTimeout(silenceTimer);
      clearTimeout(listenRestartTimer);
      if (voiceRecognition) {
        try { voiceRecognition.abort(); } catch (error) {
          if (error.name !== 'InvalidStateError') console.warn('Could not pause interview speech recognition:', error);
        }
      }
      window.speechSynthesis?.pause();
      updateVoiceControls();
      setVoiceStatus('Entretien vocal en pause. Reprenez quand vous êtes prêt.');
    }

    function resumeVoiceConversation() {
      if ((!voiceMode && introState !== 'playing') || !voicePaused) return;
      voicePaused = false;
      updateVoiceControls();
      window.speechSynthesis?.resume();
      if (voiceMode && voiceSpeaking) {
        setVoiceStatus('Madame Gloria reprend la parole…');
      } else if (voiceMode) {
        startVoiceListening();
      }
    }

    function stopVoiceConversation() {
      if (introState === 'playing') introState = 'stopped';
      voiceSessionId += 1;
      setVoiceMode(false);
      voiceSpeaking = false;
      voiceSubmitting = false;
      clearTimeout(silenceTimer);
      clearTimeout(listenRestartTimer);
      window.speechSynthesis?.cancel();
      if (voiceRecognition) {
        try { voiceRecognition.abort(); } catch (error) {
          if (error.name !== 'InvalidStateError') console.warn('Could not stop interview speech recognition:', error);
        }
      }
      window.dispatchEvent(new CustomEvent('speechSynthesisEnd'));
      updateVoiceControls();
    }

    function speakInterviewText(text) {
      return new Promise((resolve, reject) => {
        if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) {
          reject(new Error('La synthèse vocale n’est pas prise en charge par ce navigateur.'));
          return;
        }

        const utterance = new window.SpeechSynthesisUtterance(text);
        utterance.lang = 'fr-FR';
        utterance.rate = 0.9;
        const frenchVoice = getFrenchVoice();
        if (frenchVoice) utterance.voice = frenchVoice;
        utterance.onstart = () => {
          voiceSpeaking = true;
          if (voiceRecognition) {
            try { voiceRecognition.stop(); } catch (error) {
              if (error.name !== 'InvalidStateError') console.warn('Could not pause speech recognition:', error);
            }
          }
          setVoiceStatus('Madame Gloria vous parle…');
          window.dispatchEvent(new CustomEvent('speechSynthesisStart'));
        };
        utterance.onend = () => {
          voiceSpeaking = false;
          window.dispatchEvent(new CustomEvent('speechSynthesisEnd'));
          resolve();
        };
        utterance.onerror = event => {
          voiceSpeaking = false;
          window.dispatchEvent(new CustomEvent('speechSynthesisEnd'));
          reject(new Error(`La lecture vocale a échoué (${event.error}).`));
        };
        window.speechSynthesis.speak(utterance);
      });
    }

    async function playInterviewIntroduction() {
      const activeQuestion = document.getElementById('activeQuestionText')?.textContent?.trim();
      if (!activeQuestion) return;
      introState = 'playing';
      updateVoiceControls();
      await speakInterviewText(
        'Bonjour Madame, bonjour Monsieur. Bienvenue à l’entretien d’embauche. '
        + 'Sentez-vous à l’aise. Voici votre première question.'
      );
      await speakInterviewText(activeQuestion);
      introState = 'complete';
      updateVoiceControls();
    }

    const firstQuestion = document.getElementById('activeQuestionText')?.textContent?.trim();
    if (firstQuestion && window.speechSynthesis && window.SpeechSynthesisUtterance) {
      introState = 'playing';
      updateVoiceControls();
      introPromise = playInterviewIntroduction().catch(error => {
        if (introState === 'stopped') return;
        introState = 'pending';
        updateVoiceControls();
        setVoiceStatus(
          'L’accueil vocal automatique n’a pas pu démarrer. Cliquez sur « Démarrer l’entretien vocal » pour l’entendre.',
          'error',
        );
        console.warn('Automatic interview introduction could not play:', error);
      });
    }

    function appendVoiceExchange(question, response) {
      const dialogue = document.getElementById('dialogueScroll');
      const banner = dialogue?.querySelector('.active-question-banner');
      if (!dialogue || !banner) return;

      for (const [speaker, text, className] of [
        ['Madame Gloria · Recruteuse', question, 'recruiter-bubble'],
        ['Vous (Candidat)', response, 'candidate-bubble'],
      ]) {
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${className}`;
        const tag = document.createElement('div');
        tag.className = 'bubble-tag';
        tag.textContent = speaker;
        const message = document.createElement('div');
        message.className = 'bubble-text';
        message.textContent = text;
        bubble.append(tag, message);
        dialogue.insertBefore(bubble, banner);
      }
      dialogue.scrollTop = dialogue.scrollHeight;
    }

    async function submitVoiceAnswer() {
      if (!voiceMode || voiceSubmitting || answer.value.trim().length < 2) return;
      const sessionId = voiceSessionId;
      voiceSubmitting = true;
      clearTimeout(silenceTimer);
      setVoiceStatus('Merci, Madame Gloria prépare la prochaine question…');
      try {
        if (voiceRecognition) voiceRecognition.stop();
      } catch (error) {
        if (error.name !== 'InvalidStateError') console.warn('Could not pause interview speech recognition:', error);
      }

      try {
        const response = await fetch(form.action, {
          method: 'POST',
          body: new FormData(form),
          headers: { Accept: 'application/json' },
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'La réponse n’a pas pu être enregistrée.');
        if (!voiceMode || sessionId !== voiceSessionId) return;

        const submittedAnswer = answer.value.trim();
        const activeQuestion = document.getElementById('activeQuestionText')?.textContent?.trim() || '';
        appendVoiceExchange(activeQuestion, submittedAnswer);
        const progress = document.querySelector('.room-progress-badge .progress-num');
        const progressFill = document.querySelector('.room-progress-fill');
        if (progress) progress.textContent = result.answered_count;
        if (progressFill) progressFill.style.width = `${result.answered_count * 10}%`;

        if (result.completed) {
          stopVoiceConversation();
          const banner = document.querySelector('.active-question-banner');
          if (banner) {
            banner.className = 'interview-celebration';
            banner.textContent = 'Félicitations, simulation terminée ! Vous avez répondu aux 10 questions.';
          }
          controls.closest('.answer-interactive-dock')?.remove();
          setVoiceStatus('Simulation terminée. Bravo !');
          return;
        }

        const questionText = document.getElementById('activeQuestionText');
        const questionNumber = document.querySelector('.badge-question-num');
        const replayButton = document.getElementById('playActiveBtn');
        if (questionText) questionText.textContent = result.question;
        if (questionNumber) questionNumber.textContent = `QUESTION ${result.question_number} / 10`;
        if (replayButton) replayButton.dataset.question = result.question;
        answer.value = '';
        answer.dispatchEvent(new Event('input', { bubbles: true }));
        voiceTranscript = '';
        voiceSubmitting = false;
        if (!voiceMode || voicePaused) {
          setVoiceStatus('Réponse enregistrée. Reprenez l’entretien vocal quand vous êtes prêt.');
          return;
        }
        await speakInterviewText('Merci pour votre réponse.');
        if (!voiceMode || sessionId !== voiceSessionId) return;
        await speakInterviewText(result.question);
        if (!voiceMode || sessionId !== voiceSessionId) return;
        startVoiceListening();
      } catch (error) {
        if (!voiceMode || sessionId !== voiceSessionId) return;
        stopVoiceConversation();
        setVoiceStatus(`${error.message} Votre réponse est conservée ; vous pouvez la renvoyer ou reprendre l’entretien vocal.`, 'error');
      }
    }

    voiceStartButton?.addEventListener('click', async () => {
      if (recorder?.state === 'recording') {
        setVoiceStatus('Arrêtez d’abord l’enregistrement en cours avant de démarrer la conversation vocale.', 'error');
        return;
      }
      if (!SpeechRecognition) {
        setVoiceStatus('La conversation vocale automatique nécessite Chrome ou Edge. Vous pouvez écrire votre réponse ou utiliser la transcription audio.', 'error');
        return;
      }
      if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) {
        setVoiceStatus('La synthèse vocale n’est pas prise en charge par ce navigateur. Vous pouvez répondre par écrit.', 'error');
        return;
      }

      voiceRecognition = new SpeechRecognition();
      voiceRecognition.lang = 'fr-FR';
      voiceRecognition.continuous = true;
      voiceRecognition.interimResults = true;
      voiceRecognition.onresult = event => {
        if (!voiceMode || voicePaused) return;
        let interimTranscript = '';
        let finalTranscript = '';
        for (let index = event.resultIndex; index < event.results.length; index += 1) {
          const transcript = event.results[index][0].transcript;
          if (event.results[index].isFinal) finalTranscript += `${transcript} `;
          else interimTranscript += transcript;
        }
        if (finalTranscript) {
          voiceTranscript = `${voiceTranscript} ${finalTranscript}`.trim();
          answer.value = voiceTranscript;
          answer.dispatchEvent(new Event('input', { bubbles: true }));
          clearTimeout(silenceTimer);
          silenceTimer = setTimeout(submitVoiceAnswer, 3000);
        }
        if (interimTranscript) setVoiceStatus(`Je vous écoute… « ${interimTranscript} »`);
        else if (voiceMode && !voicePaused && !voiceSubmitting) setVoiceStatus('Je vous écoute. Prenez votre temps.');
      };
      voiceRecognition.onerror = event => {
        console.warn('Interview speech recognition error:', event.error);
        if (!voiceMode || voicePaused || event.error === 'no-speech' || event.error === 'aborted') return;
        stopVoiceConversation();
        setVoiceStatus(
          event.error === 'not-allowed' || event.error === 'service-not-allowed'
            ? 'Autorisez le microphone et la reconnaissance vocale dans votre navigateur, puis réessayez.'
            : 'La reconnaissance vocale est indisponible. Vous pouvez écrire votre réponse ou utiliser la transcription audio.',
          'error',
        );
      };
      voiceRecognition.onend = () => {
        if (!voiceMode || voicePaused || voiceSpeaking || voiceSubmitting) return;
        if (answer.value.trim().length >= 2) {
          clearTimeout(silenceTimer);
          silenceTimer = setTimeout(submitVoiceAnswer, 3000);
        }
        else {
          setVoiceStatus('Je vous écoute. Prenez votre temps.');
          clearTimeout(listenRestartTimer);
          listenRestartTimer = setTimeout(startVoiceListening, 350);
        }
      };

      setVoiceMode(true);
      const sessionId = ++voiceSessionId;
      voiceTranscript = '';
      answer.value = '';
      answer.dispatchEvent(new Event('input', { bubbles: true }));
      const activeQuestion = document.getElementById('activeQuestionText')?.textContent?.trim();
      if (!activeQuestion) {
        stopVoiceConversation();
        setVoiceStatus('Aucune question en attente dans cette simulation.', 'error');
        return;
      }

      try {
        if (introState === 'playing' && introPromise) {
          await introPromise;
        } else if (introState !== 'complete') {
          await playInterviewIntroduction();
        }
        if (!voiceMode || sessionId !== voiceSessionId) return;
        startVoiceListening();
      } catch (error) {
        if (!voiceMode || sessionId !== voiceSessionId) return;
        stopVoiceConversation();
        setVoiceStatus(error.message, 'error');
      }
    });

    voicePauseButton?.addEventListener('click', pauseVoiceConversation);
    voiceResumeButton?.addEventListener('click', resumeVoiceConversation);
    voiceStopButton?.addEventListener('click', () => {
      stopVoiceConversation();
      setVoiceStatus('Entretien vocal arrêté. Vous pouvez le redémarrer quand vous le souhaitez.');
    });

    recordButton.addEventListener('click', async () => {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
        setStatus('L’enregistrement audio n’est pas pris en charge par ce navigateur.', 'error');
        return;
      }

      audioBlob = undefined;
      chunks = [];
      const requestId = ++recordingRequestId;
      recorder = undefined;
      recordButton.disabled = true;
      stopButton.disabled = false;
      setStatus('Démarrage du microphone…');
      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (requestId !== recordingRequestId) {
          mediaStream.getTracks().forEach(track => track.stop());
          return;
        }
        stream = mediaStream;
        if (liveRecognition) {
          try { liveRecognition.start(); } catch (error) {
            console.warn('Live speech recognition could not start:', error);
          }
        }
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
        if (requestId !== recordingRequestId) return;
        if (stream) stream.getTracks().forEach(track => track.stop());
        stream = undefined;
        stopButton.disabled = true;
        recordButton.disabled = false;
        setStatus('Impossible d’accéder au microphone. Vérifiez les autorisations du navigateur.', 'error');
        console.error('Microphone unavailable:', error);
      }
    });

    stopButton.addEventListener('click', () => {
      if (recorder?.state !== 'recording' && recordButton.disabled) {
        recordingRequestId += 1;
        stopButton.disabled = true;
        recordButton.disabled = false;
        setStatus('Demande d’accès au microphone annulée.');
        return;
      }
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

// ── 17. CV presentation pitch ──────────────────────────────────
(function initPitchGenerator() {
  const form = document.getElementById('pitch-form');
  const status = document.getElementById('pitch-status');
  const output = document.getElementById('pitch-output');
  const pitchText = document.getElementById('pitch-text');
  const generateButton = document.getElementById('pitch-generate');
  const playButton = document.getElementById('pitch-play');
  const stopButton = document.getElementById('pitch-stop');
  if (!form || !status || !output || !pitchText || !generateButton || !playButton || !stopButton) return;

  let pitch = '';

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    generateButton.disabled = true;
    status.textContent = 'Création du pitch à partir de votre CV…';

    try {
      const response = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { Accept: 'application/json' },
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Impossible de créer le pitch. Réessayez.');

      pitch = data.pitch;
      pitchText.textContent = pitch;
      output.hidden = false;
      playButton.disabled = !('speechSynthesis' in window);
      stopButton.disabled = !('speechSynthesis' in window);
      status.textContent = playButton.disabled
        ? 'Le pitch est prêt, mais la lecture vocale n’est pas prise en charge par ce navigateur.'
        : 'Votre pitch est prêt. Vous pouvez l’écouter et le relire avant votre entretien.';
    } catch (error) {
      status.textContent = error.message || 'Impossible de créer le pitch. Réessayez.';
    } finally {
      generateButton.disabled = false;
    }
  });

  playButton.addEventListener('click', () => {
    if (!pitch || !('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(pitch);
    utterance.lang = 'fr-FR';
    const frenchVoice = window.speechSynthesis.getVoices().find(voice => voice.lang.toLowerCase().startsWith('fr'));
    if (frenchVoice) utterance.voice = frenchVoice;
    window.speechSynthesis.speak(utterance);
  });

  stopButton.addEventListener('click', () => window.speechSynthesis.cancel());
})();
