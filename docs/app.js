/**
 * Talk-me — Landing Page Interactive Experience
 * Zero-dependency, lightweight, accessible and high-performance.
 * Features:
 * - Real Microphone SpeechRecognition (Web Speech API) with graceful fallback
 * - Real-time Audio Reactive Canvas Waveform (Web Audio API)
 * - Safe Whitespace Typewriter (document.createTextNode + appendData)
 * - 3D Card Hover Perspective
 * - Accessible FAQ Accordion
 */

document.addEventListener('DOMContentLoaded', () => {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // -------------------------------------------------------------
  // 1. Audio Waveform Canvas Animation
  // -------------------------------------------------------------
  const canvas = document.getElementById('waveformCanvas');
  const ctx = canvas ? canvas.getContext('2d') : null;

  let wavePhase = 0;
  let currentAmplitude = 0.15; // idle amplitude
  let targetAmplitude = 0.15;

  function resizeCanvas() {
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    if (ctx) ctx.scale(dpr, dpr);
  }

  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  function drawWaveform() {
    if (!canvas || !ctx) return;

    const width = canvas.getBoundingClientRect().width;
    const height = canvas.getBoundingClientRect().height;
    const centerY = height / 2;

    ctx.clearRect(0, 0, width, height);

    // Smoothly interpolate amplitude
    currentAmplitude += (targetAmplitude - currentAmplitude) * 0.12;

    // Draw multi-layered sine waves
    const layers = [
      { color: 'rgba(99, 102, 241, 0.25)', speed: 0.04, freq: 0.015, ampMultiplier: 0.6 },
      { color: 'rgba(124, 58, 237, 0.4)', speed: 0.07, freq: 0.02, ampMultiplier: 0.85 },
      { color: 'rgba(6, 182, 212, 0.85)', speed: 0.09, freq: 0.025, ampMultiplier: 1.1 }
    ];

    layers.forEach(layer => {
      ctx.beginPath();
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = layer.color;
      ctx.lineCap = 'round';

      for (let x = 0; x < width; x += 3) {
        // Window envelope to taper edges gently at left and right
        const envelope = Math.sin((x / width) * Math.PI);
        const y = centerY + Math.sin(x * layer.freq + wavePhase * layer.speed) *
                           (currentAmplitude * height * 0.42 * envelope);

        if (x === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();
    });

    if (!prefersReducedMotion) {
      wavePhase += 1;
      requestAnimationFrame(drawWaveform);
    }
  }

  if (!prefersReducedMotion) {
    drawWaveform();
  }

  // -------------------------------------------------------------
  // 2. Interactive Voice Dictation Simulator (Real Mic + Fallback)
  // -------------------------------------------------------------
  const micButton = document.getElementById('micButton');
  const statusBadge = document.getElementById('statusBadge');
  const demoOutput = document.getElementById('demoOutput');
  const clearDemoBtn = document.getElementById('clearDemoBtn');
  const presetButtons = document.querySelectorAll('.preset-btn');

  let isRecording = false;
  let isProcessing = false;
  let typeInterval = null;

  // Real Speech Recognition Support (Web Speech API)
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  let liveTranscript = '';
  let recognitionActive = false;

  // Real Audio Level Analyser via getUserMedia
  let audioContext = null;
  let analyser = null;
  let micAudioInitialized = false;

  async function tryInitAudioAnalyser() {
    if (micAudioInitialized || !navigator.mediaDevices?.getUserMedia) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioContext.createMediaStreamSource(stream);
      analyser = audioContext.createAnalyser();
      analyser.fftSize = 64;
      source.connect(analyser);
      micAudioInitialized = true;

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      function trackMicVolume() {
        if (isRecording && analyser) {
          analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const avg = sum / dataArray.length;
          // React smoothly to real voice volume
          targetAmplitude = Math.max(0.35, Math.min(1.4, (avg / 100) * 1.2));
        }
        requestAnimationFrame(trackMicVolume);
      }
      trackMicVolume();
    } catch (e) {
      // User dismissed microphone prompt or device not present; fallback to synthetic pulse
      micAudioInitialized = true;
    }
  }

  if (SpeechRecognition) {
    try {
      recognition = new SpeechRecognition();
      recognition.lang = 'es-ES';
      recognition.continuous = true;
      recognition.interimResults = true;

      recognition.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            liveTranscript += event.results[i][0].transcript + ' ';
          } else {
            interim += event.results[i][0].transcript;
          }
        }
        const currentSpoken = (liveTranscript + interim).trim();
        if (currentSpoken && statusBadge) {
          const preview = currentSpoken.length > 28 ? '...' + currentSpoken.slice(-28) : currentSpoken;
          statusBadge.textContent = `● Escuchando: "${preview}"`;
        }
      };

      recognition.onerror = () => {
        // Silently handled; stopRecording will fallback cleanly
      };

      recognition.onend = () => {
        recognitionActive = false;
      };
    } catch (e) {
      recognition = null;
    }
  }

  const samplePhrases = [
    "Hola, estoy redactando este documento usando Talk-me. La velocidad y precisión de Whisper local es increíble.",
    "Estimado equipo, los resultados del último sprint superaron las expectativas en un 40%.",
    "Función asíncrona que procesa el flujo de audio y lo envía al modelo CTranslate2 sin latencia de red.",
    "El dictado offline garantiza que nuestras notas confidenciales jamás salgan del equipo."
  ];
  let phraseIndex = 0;
  let customPresetText = null;

  function startRecording(presetText) {
    if (isRecording || isProcessing) return;
    isRecording = true;
    liveTranscript = '';
    customPresetText = presetText || null;

    // Try connecting real mic audio for live waveform reaction
    if (!micAudioInitialized) {
      tryInitAudioAnalyser();
    }

    // Start native Web Speech API if no fixed preset text
    if (!presetText && recognition && !recognitionActive) {
      try {
        recognition.start();
        recognitionActive = true;
      } catch (e) {
        recognitionActive = false;
      }
    }

    // Update UI state
    micButton.classList.add('recording');
    statusBadge.className = 'status-indicator recording';
    statusBadge.textContent = '● Grabando audio...';
    targetAmplitude = 0.95; // Default reactive amplitude

    // Clear placeholder text if first time
    const placeholder = demoOutput.querySelector('.placeholder-text');
    if (placeholder) {
      demoOutput.innerHTML = '';
    }
  }

  function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    isProcessing = true;

    // Stop speech recognition
    if (recognition && recognitionActive) {
      try {
        recognition.stop();
      } catch (e) {}
      recognitionActive = false;
    }

    // Transition to processing state
    micButton.classList.remove('recording');
    statusBadge.className = 'status-indicator processing';
    statusBadge.textContent = 'Transcribiendo con Whisper (<0.5s)...';
    targetAmplitude = 0.25;

    // Simulate Whisper <0.5s ultra-fast local latency
    setTimeout(() => {
      isProcessing = false;
      targetAmplitude = 0.15; // return to idle
      statusBadge.className = 'status-indicator ready';
      statusBadge.textContent = 'Listo para dictar';

      // Decide what text to write:
      // 1. If user spoke real words into their mic, use their REAL voice transcript!
      // 2. If a preset button was clicked, use the preset text.
      // 3. Fallback to smart rotating sample phrases.
      let finalText = '';
      if (liveTranscript && liveTranscript.trim().length > 0) {
        finalText = liveTranscript.trim();
      } else if (customPresetText) {
        finalText = customPresetText;
      } else {
        finalText = samplePhrases[phraseIndex % samplePhrases.length];
        phraseIndex++;
      }

      typeWriterOutput(finalText);
    }, 400);
  }

  /**
   * Safe Typewriter effect that preserves all spaces, tabs and newlines
   * using DOM TextNode appendData rather than innerText.
   */
  function typeWriterOutput(text) {
    if (typeInterval) clearInterval(typeInterval);

    // Remove placeholder if present
    const placeholder = demoOutput.querySelector('.placeholder-text');
    if (placeholder) {
      demoOutput.innerHTML = '';
    } else if (demoOutput.textContent.trim().length > 0) {
      // Append a separating space for consecutive dictations
      demoOutput.appendChild(document.createTextNode(' '));
    }

    // Create a new TextNode to stream characters into
    const textNode = document.createTextNode('');
    demoOutput.appendChild(textNode);

    let i = 0;
    typeInterval = setInterval(() => {
      if (i < text.length) {
        textNode.appendData(text.charAt(i));
        i++;
        // Keep scroll at bottom
        demoOutput.scrollTop = demoOutput.scrollHeight;
      } else {
        clearInterval(typeInterval);
        typeInterval = null;
      }
    }, 18);
  }

  // Pointer events on Mic Button (supports both press-and-hold and click toggle)
  if (micButton) {
    let isHolding = false;

    micButton.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      isHolding = true;
      startRecording();
    });

    window.addEventListener('pointerup', () => {
      if (isHolding) {
        isHolding = false;
        stopRecording();
      }
    });

    // Keyboard Spacebar Hold to Dictate when simulator is active
    window.addEventListener('keydown', (e) => {
      if (e.code === 'Space' && !e.repeat && document.activeElement !== demoOutput && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
        e.preventDefault();
        startRecording();
      }
    });

    window.addEventListener('keyup', (e) => {
      if (e.code === 'Space' && isRecording) {
        e.preventDefault();
        stopRecording();
      }
    });
  }

  // Preset buttons handler
  presetButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const text = btn.getAttribute('data-text');
      startRecording(text);
      setTimeout(() => {
        stopRecording();
      }, 700);
    });
  });

  // Clear demo text button
  if (clearDemoBtn) {
    clearDemoBtn.addEventListener('click', () => {
      if (typeInterval) clearInterval(typeInterval);
      demoOutput.innerHTML = '<span class="placeholder-text">Presiona y mantén presionado el botón del micrófono abajo para iniciar el dictado...</span>';
    });
  }

  // -------------------------------------------------------------
  // 3. 3D Card Hover Perspective Tilt
  // -------------------------------------------------------------
  if (!prefersReducedMotion) {
    const tiltCards = document.querySelectorAll('.bento-card, .simulator-card, .comparison-table-wrapper');

    tiltCards.forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        const rotateX = ((y - centerY) / centerY) * -3.5;
        const rotateY = ((x - centerX) / centerX) * 3.5;

        card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-2px)`;
      });

      card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0px)';
      });
    });
  }

  // -------------------------------------------------------------
  // 4. Smooth Anchor Link Scrolling with Sticky Header Offset
  // -------------------------------------------------------------
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;

      const targetElement = document.querySelector(targetId);
      if (targetElement) {
        e.preventDefault();
        const headerOffset = 80;
        const elementPosition = targetElement.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

        window.scrollTo({
          top: offsetPosition,
          behavior: prefersReducedMotion ? 'auto' : 'smooth'
        });
      }
    });
  });

  // -------------------------------------------------------------
  // 5. Exclusive FAQ Accordion Toggle
  // -------------------------------------------------------------
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach(item => {
    item.addEventListener('toggle', () => {
      if (item.open) {
        faqItems.forEach(otherItem => {
          if (otherItem !== item && otherItem.open) {
            otherItem.removeAttribute('open');
          }
        });
      }
    });
  });
});
