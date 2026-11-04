(() => {
  const app = document.getElementById('assistantApp');
  if (!app) return;

  const csrfToken = app.dataset.csrfToken;
  const conversationsUrl = app.dataset.conversationsUrl;
  const conversationUrl = app.dataset.conversationUrl;
  const messageUrl = app.dataset.messageUrl;
  const audioUrl = app.dataset.audioUrl;
  const list = document.getElementById('assistantConversationList');
  const messages = document.getElementById('assistantMessages');
  const status = document.getElementById('assistantStatus');
  const form = document.getElementById('assistantMessageForm');
  const input = document.getElementById('assistantMessageInput');
  const language = document.getElementById('assistantLanguage');
  const useContext = document.getElementById('assistantUseContext');
  const cvSelect = document.getElementById('assistantCv');
  const autoSpeak = document.getElementById('assistantAutoSpeak');
  const deleteButton = document.getElementById('assistantDeleteConversation');
  const recordButton = document.getElementById('assistantRecordAudio');
  let activeConversation;
  let mediaRecorder;
  let audioChunks = [];
  let audioRequestId = 0;
  let audioRequestPending = false;

  async function requestJson(url, options = {}) {
    const response = await fetch(url, options);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'La demande a échoué. Réessayez.');
    return result;
  }

  function conversationEndpoint(template, id) {
    return template.replace(/\/1$/, `/${id}`);
  }

  function setStatus(message, isError = false) {
    status.textContent = message;
    status.dataset.state = isError ? 'error' : '';
  }

  function renderMessage(message) {
    const item = document.createElement('article');
    item.className = `assistant-message assistant-message-${message.role}`;
    const label = document.createElement('strong');
    label.textContent = message.role === 'assistant' ? 'CVBoost AI' : 'Vous';
    const content = document.createElement('p');
    content.textContent = message.content;
    item.append(label, content);
    if (message.role === 'assistant') {
      const play = document.createElement('button');
      play.type = 'button';
      play.className = 'assistant-play-message';
      play.textContent = 'Écouter';
      play.addEventListener('click', () => speak(message.content));
      item.append(play);
    }
    messages.append(item);
  }

  function renderConversationList(conversations) {
    list.replaceChildren();
    if (!conversations.length) {
      const empty = document.createElement('p');
      empty.className = 'assistant-empty-list';
      empty.textContent = 'Aucune conversation pour le moment.';
      list.append(empty);
      return;
    }
    for (const conversation of conversations) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'assistant-conversation-link';
      button.dataset.conversationId = conversation.id;
      button.textContent = conversation.title;
      if (activeConversation?.id === conversation.id) button.classList.add('active');
      list.append(button);
    }
  }

  function setConversationSettingsEditable(editable) {
    language.disabled = !editable;
    useContext.disabled = !editable;
    cvSelect.disabled = !editable || !useContext.checked;
  }

  function speak(text) {
    if (!('speechSynthesis' in window) || !window.SpeechSynthesisUtterance) {
      setStatus('La lecture vocale n’est pas prise en charge par ce navigateur.', true);
      return;
    }
    const voices = window.speechSynthesis.getVoices();
    const languagePrefix = language.value === 'ln' ? 'lin' : 'fr';
    const voice = voices.find(item => item.lang?.toLowerCase().startsWith(languagePrefix));
    if (language.value === 'ln' && !voice) {
      setStatus('Aucune voix Lingala n’est disponible dans ce navigateur. La réponse reste accessible en texte.', true);
      return;
    }
    const utterance = new window.SpeechSynthesisUtterance(text);
    utterance.lang = language.value === 'ln' ? 'lin-Latn' : 'fr-FR';
    if (voice) utterance.voice = voice;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }

  async function refreshConversations() {
    const result = await requestJson(conversationsUrl);
    renderConversationList(result.conversations);
  }

  async function openConversation(id) {
    const conversation = await requestJson(conversationEndpoint(conversationUrl, id));
    activeConversation = conversation;
    language.value = conversation.language;
    useContext.checked = conversation.use_personal_context;
    cvSelect.value = conversation.context_cv_id || '';
    setConversationSettingsEditable(false);
    deleteButton.disabled = false;
    messages.replaceChildren();
    if (!conversation.messages.length) {
      const welcome = document.createElement('p');
      welcome.className = 'assistant-welcome';
      welcome.textContent = 'Posez votre première question à CVBoost AI.';
      messages.append(welcome);
    } else {
      conversation.messages.forEach(renderMessage);
    }
    messages.scrollTop = messages.scrollHeight;
    await refreshConversations();
  }

  async function createConversation() {
    const data = {
      language: language.value,
      use_personal_context: useContext.checked,
      cv_id: useContext.checked ? Number(cvSelect.value) : null,
    };
    const result = await requestJson(conversationsUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify(data),
    });
    await openConversation(result.id);
    setStatus('');
  }

  list.addEventListener('click', event => {
    const button = event.target.closest('[data-conversation-id]');
    if (!button) return;
    openConversation(Number(button.dataset.conversationId)).catch(error => setStatus(error.message, true));
  });

  document.getElementById('assistantNewConversation').addEventListener('click', () => {
    activeConversation = undefined;
    deleteButton.disabled = true;
    setConversationSettingsEditable(true);
    messages.replaceChildren();
    const welcome = document.createElement('p');
    welcome.className = 'assistant-welcome';
    welcome.textContent = 'Posez votre première question à CVBoost AI.';
    messages.append(welcome);
    input.focus();
    setStatus('Nouvelle conversation prête.');
  });

  useContext.addEventListener('change', () => {
    cvSelect.disabled = !useContext.checked;
  });
  setConversationSettingsEditable(!activeConversation);

  deleteButton.addEventListener('click', async () => {
    if (!activeConversation || !window.confirm('Supprimer cette conversation et ses messages ?')) return;
    try {
      await requestJson(conversationEndpoint(conversationUrl, activeConversation.id), {
        method: 'DELETE',
        headers: { 'X-CSRFToken': csrfToken },
      });
      activeConversation = undefined;
      deleteButton.disabled = true;
      messages.replaceChildren();
      await refreshConversations();
      setStatus('Conversation supprimée.');
    } catch (error) {
      setStatus(error.message, true);
    }
  });

  form.addEventListener('submit', async event => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    const sendButton = document.getElementById('assistantSendMessage');
    sendButton.disabled = true;
    setStatus('CVBoost AI prépare une réponse…');
    try {
      if (!activeConversation) await createConversation();
      const result = await requestJson(
        conversationEndpoint(messageUrl, activeConversation.id),
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
          },
          body: JSON.stringify({ message: text }),
        },
      );
      messages.querySelector('.assistant-welcome')?.remove();
      renderMessage(result.user_message);
      renderMessage(result.assistant_message);
      input.value = '';
      messages.scrollTop = messages.scrollHeight;
      await refreshConversations();
      setStatus('');
      if (autoSpeak.checked) speak(result.assistant_message.content);
    } catch (error) {
      setStatus(error.message, true);
    } finally {
      sendButton.disabled = false;
      input.focus();
    }
  });

  recordButton.addEventListener('click', async () => {
    if (mediaRecorder?.state === 'recording') {
      mediaRecorder.stop();
      return;
    }
    if (audioRequestPending) {
      audioRequestId += 1;
      audioRequestPending = false;
      recordButton.textContent = 'Enregistrer une question';
      setStatus('Demande d’accès au microphone annulée.');
      return;
    }
    if (language.value !== 'fr') {
      setStatus('La transcription vocale Lingala n’est pas prise en charge. Saisissez votre message en texte.', true);
      return;
    }
    if (!activeConversation) {
      setStatus('Démarrez ou sélectionnez une conversation avant d’enregistrer.', true);
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setStatus('L’enregistrement audio n’est pas pris en charge dans ce navigateur.', true);
      return;
    }

    const requestId = ++audioRequestId;
    audioRequestPending = true;
    recordButton.textContent = 'Annuler la demande de micro';
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (requestId !== audioRequestId) {
        stream.getTracks().forEach(track => track.stop());
        return;
      }
      audioRequestPending = false;
      const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4']
        .find(type => window.MediaRecorder.isTypeSupported(type));
      mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
      audioChunks = [];
      mediaRecorder.addEventListener('dataavailable', event => {
        if (event.data.size) audioChunks.push(event.data);
      });
      mediaRecorder.addEventListener('stop', async () => {
        stream.getTracks().forEach(track => track.stop());
        recordButton.disabled = true;
        setStatus('Transcription en cours…');
        const audio = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
        const payload = new FormData();
        const extension = audio.type.includes('mp4') ? 'mp4' : 'webm';
        payload.append('audio', audio, `question.${extension}`);
        try {
          const result = await requestJson(
            conversationEndpoint(audioUrl, activeConversation.id),
            {
              method: 'POST',
              headers: { 'X-CSRFToken': csrfToken },
              body: payload,
            },
          );
          input.value = result.transcript;
          input.focus();
          setStatus('Transcription prête. Relisez-la puis envoyez votre message.');
        } catch (error) {
          setStatus(error.message, true);
        } finally {
          recordButton.disabled = false;
          recordButton.textContent = 'Enregistrer une question';
        }
      }, { once: true });
      mediaRecorder.start();
      recordButton.textContent = 'Arrêter l’enregistrement';
      setStatus('Enregistrement en cours. L’audio ne sera pas conservé.');
    } catch (error) {
      if (requestId !== audioRequestId) return;
      audioRequestPending = false;
      if (stream) stream.getTracks().forEach(track => track.stop());
      recordButton.textContent = 'Enregistrer une question';
      setStatus('Impossible d’accéder au microphone. Vérifiez les autorisations du navigateur.', true);
      console.error('Assistant microphone unavailable:', error);
    }
  });

  refreshConversations().catch(error => setStatus(error.message, true));
  const initialConversation = list.querySelector('[data-conversation-id]');
  if (initialConversation) {
    openConversation(Number(initialConversation.dataset.conversationId))
      .catch(error => setStatus(error.message, true));
  }
})();
