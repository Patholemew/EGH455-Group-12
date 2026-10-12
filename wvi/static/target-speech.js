"use strict";

const SPEECH_COOLDOWN_MS = 10000;

function spokenTarget(target) {
  if (target.type === "valve") {
    if (target.valve_state === "open") return "Open valve detected.";
    if (target.valve_state === "closed") return "Closed valve detected.";
    return "Valve detected. State unknown.";
  }
  if (target.type === "aruco") return "ArUco marker " + target.marker_id + " detected.";
  if (target.type === "gauge") {
    if (!Number.isFinite(target.gauge_reading)) return "Gauge detected. Reading unavailable.";
    const gaugeUnit = target.gauge_unit === "UNIT" ? "BAR" : target.gauge_unit;
    const unit = gaugeUnit ? " " + gaugeUnit : "";
    return "Gauge detected. Reading " + target.gauge_reading.toFixed(2) + unit + ".";
  }
  return "Target detected.";
}

class TargetSpeech {
  constructor(status) {
    this.status = status;
    this.synth = window.speechSynthesis;
    this.supported = Boolean(this.synth && window.SpeechSynthesisUtterance);
    this.ready = Boolean(window.navigator?.userActivation?.hasBeenActive);
    this.targets = [];
    this.updatedAt = 0;
    this.announced = new Map();
    this.utterance = null;
    this.speakingKeys = [];
    this.lastSpokenAt = -Infinity;
    if (!this.supported) {
      status.textContent = "Speech is not supported by this browser.";
      status.hidden = false;
      return;
    }
    // Browser audio permission comes from normal page interaction, not a toggle.
    const allowSpeech = () => {
      if (this.ready) return;
      this.ready = true;
      this.showMode();
      this.announce();
    };
    document.addEventListener("click", allowSpeech);
    document.addEventListener("keydown", allowSpeech);
    this.showMode();
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) this.stop();
    });
    window.addEventListener("pagehide", () => this.stop());
  }

  identity(target) {
    return JSON.stringify([target.type, target.event_id, target.marker_id]);
  }

  key(target) {
    // Capture IDs/timestamps and fluctuating gauge readings must not repeat alerts.
    return this.identity(target) + ":" + (target.type === "valve" ? target.valve_state : "");
  }

  currentTargets() {
    const elapsed = (performance.now() - this.updatedAt) / 1000;
    return this.targets.filter(target => !target.stale && target.age_seconds + elapsed <= 4);
  }

  showMode() {
    this.status.hidden = this.ready;
    this.status.textContent = this.ready
      ? ""
      : "Click or tap anywhere on this page to allow announcements.";
  }

  stop() {
    const wasSpeaking = this.utterance;
    // Clear first: cancellation can fire an error event for the old utterance.
    this.utterance = null;
    this.speakingKeys = [];
    if (wasSpeaking) this.synth.cancel();
    this.showMode();
  }

  update(targets) {
    if (!this.supported) return;
    this.targets = targets;
    this.updatedAt = performance.now();
    const current = this.currentTargets();
    const identities = new Set(current.map(target => this.identity(target)));
    const keys = new Set(current.map(target => this.key(target)));
    for (const [identity, record] of this.announced) {
      if (this.updatedAt - record.lastSeen >= 10000) this.announced.delete(identity);
      else if (identities.has(identity)) record.lastSeen = this.updatedAt;
    }
    if (this.speakingKeys.some(key => !keys.has(key))) {
      this.stop();
    }
    this.announce();
  }

  announce() {
    if (!this.supported || !this.ready || document.hidden || this.utterance
        || performance.now() - this.lastSpokenAt < SPEECH_COOLDOWN_MS) return false;

    const targets = this.currentTargets().filter(target =>
      this.announced.get(this.identity(target))?.key !== this.key(target));
    const text = targets.map(spokenTarget).join(" ");
    if (!text) return false;

    // SpeechSynthesisUtterance and speechSynthesis.speak() are built into the browser.
    const utterance = new window.SpeechSynthesisUtterance(text);
    // Prefer an installed English voice, including when the Pi network is offline.
    const voices = this.synth.getVoices().filter(voice => voice.localService && /^en[-_]/i.test(voice.lang));
    utterance.voice = voices.find(voice => voice.lang === "en-AU") || voices[0] || null;
    utterance.lang = utterance.voice ? utterance.voice.lang : "en-AU";
    this.utterance = utterance;
    this.speakingKeys = targets.map(target => this.key(target));
    utterance.onstart = () => {
      if (this.utterance !== utterance) return;
      this.lastSpokenAt = performance.now();
      for (const target of targets) {
        this.announced.set(this.identity(target), {key: this.key(target), lastSeen: this.lastSpokenAt});
      }
    };
    utterance.onend = () => {
      if (this.utterance !== utterance) return;
      this.utterance = null;
      this.speakingKeys = [];
      this.showMode();
      // The next dashboard refresh checks for another fresh target.
    };
    utterance.onerror = (event) => {
      if (this.utterance !== utterance) return;
      this.ready = false;
      this.stop();
      if (event?.error !== "not-allowed") {
        this.status.textContent = "Speech could not play. Check your device's voices, then click or tap to retry.";
      }
    };
    // Reserve the interval while waiting for the browser's actual start event.
    this.lastSpokenAt = performance.now();
    try {
      this.synth.speak(utterance);
    } catch (error) {
      utterance.onerror();
    }
    return true;
  }
}
