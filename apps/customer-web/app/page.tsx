"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "/backend";
const PUBLIC_APP_URL = process.env.NEXT_PUBLIC_PUBLIC_APP_URL || "";

type Section = "home" | "voice" | "stores" | "cinema" | "parking" | "navigate" | "lost" | "help";

type StoreItem = {
  id: number;
  name: string;
  unit: string | null;
  floor_id: number | null;
  description: string | null;
  nearest_landmark: string | null;
  opening_hours: string | null;
  data_status: string;
  source_name: string | null;
  source_url: string | null;
  verified_at: string | null;
  expires_at: string | null;
  map_node_code: string | null;
  discovery_priority: number;
  verification_confidence: string;
  location_confidence: string;
  public_rating: number | null;
  public_review_count: number | null;
  categories: { id: number; name: string }[];
};

type ParkingItem = {
  id: number;
  area_code: string;
  name: string;
  capacity: number | null;
  occupancy_status: string;
  source: string;
  data_status: string;
  updated_at: string;
  expires_at: string | null;
};

type RouteData = {
  from_node: string;
  to_node: string;
  total_distance_m: number;
  accessible_only: boolean;
  data_status: string;
  steps: { from_node: string; to_node: string; instruction: string; distance_m: number }[];
};

type CinemaStatus = {
  cinema_name: string;
  box_office_hours: string;
  movie_enquiry: string;
  official_booking_url: string;
  live_data_available: boolean;
};

const actions: Array<{ id: Section; title: string; copy: string }> = [
  { id: "voice", title: "Voice concierge", copy: "Speak naturally and let ENESKO guide you." },
  { id: "stores", title: "Stores", copy: "Find brands and what they sell." },
  { id: "cinema", title: "Cinema", copy: "Check Silverbird information and official booking." },
  { id: "parking", title: "Parking", copy: "See published capacity and fresh staff status." },
  { id: "navigate", title: "Navigate", copy: "Open indoor guidance and mapped destinations." },
  { id: "lost", title: "Lost & Found", copy: "Create a trackable lost-item case." },
  { id: "help", title: "Human help", copy: "Send a request directly to mall operations." },
];

export default function Home() {
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [section, setSection] = useState<Section>("home");
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [assistantStores, setAssistantStores] = useState<any[]>([]);
  const [stores, setStores] = useState<StoreItem[]>([]);
  const [parking, setParking] = useState<ParkingItem[]>([]);
  const [cinema, setCinema] = useState<CinemaStatus | null>(null);
  const [shows, setShows] = useState<any[]>([]);
  const [route, setRoute] = useState<RouteData | null>(null);
  const [routeDestination, setRouteDestination] = useState("Samsung Experience Store");
  const [supportMessage, setSupportMessage] = useState("");
  const [supportContact, setSupportContact] = useState("");
  const [lostItem, setLostItem] = useState("");
  const [lostLocation, setLostLocation] = useState("");
  const [lostFeatures, setLostFeatures] = useState("");
  const [lostContact, setLostContact] = useState("");
  const [caseRef, setCaseRef] = useState("");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [voiceSessionRef, setVoiceSessionRef] = useState("");
  const [voiceInput, setVoiceInput] = useState("");
  const [voiceState, setVoiceState] = useState<"ready" | "listening" | "thinking" | "speaking" | "paused">("ready");
  const [voiceMessages, setVoiceMessages] = useState<Array<{ role: "user" | "assistant"; text: string }>>([]);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [shareOrigin, setShareOrigin] = useState("");
  const [phoneAccessOpen, setPhoneAccessOpen] = useState(false);
  const [voicePermission, setVoicePermission] = useState<"unknown" | "granted" | "denied">("unknown");
  const [voiceLanguage, setVoiceLanguage] = useState<"en-NG" | "yo-NG">("en-NG");
  const [voiceRotation, setVoiceRotation] = useState(0);
  const [conversationActive, setConversationActive] = useState(false);
  const [visitRef, setVisitRef] = useState("");
  const recognitionRef = useRef<any>(null);
  const conversationActiveRef = useRef(false);

  useEffect(() => {
    const saved = window.localStorage.getItem("enesko-theme");
    const next =
      saved === "light" || saved === "dark"
        ? saved
        : window.matchMedia("(prefers-color-scheme: light)").matches
          ? "light"
          : "dark";
    setTheme(next);
    setShareOrigin(PUBLIC_APP_URL || window.location.origin);
    let currentVisit = window.sessionStorage.getItem("enesko-visit-ref");
    if (!currentVisit) {
      currentVisit = `VISIT-${window.crypto?.randomUUID?.() || Date.now().toString(36)}`;
      window.sessionStorage.setItem("enesko-visit-ref", currentVisit);
    }
    setVisitRef(currentVisit);
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    setSpeechSupported(Boolean(SpeechRecognition));
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("enesko-theme", theme);
  }, [theme]);

  async function readJson(response: Response, label: string) {
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(body?.detail || `${label} failed (HTTP ${response.status}).`);
    }
    return body;
  }

  async function ask(event?: FormEvent) {
    event?.preventDefault();
    if (!query.trim()) {
      setNotice("Ask ENESKO a question first.");
      return;
    }

    setLoading(true);
    setNotice("");
    setAnswer("");
    setAssistantStores([]);

    try {
      const response = await fetch(API + "/api/v1/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: query.trim(), channel: "web", session_ref: visitRef || null }),
      });
      const body = await readJson(response, "ENESKO assistant");
      setAnswer(body.answer || "No answer is currently available.");
      setAssistantStores(body.data?.stores || []);
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "ENESKO could not answer that request.");
    } finally {
      setLoading(false);
    }
  }

  function speechSafeText(
    text: string,
    language: "en-NG" | "yo-NG",
    hasExactLocaleVoice: boolean
  ) {
    let spoken = text.replace(/\bENESKO\b/g, "Enesko");

    if (language === "en-NG" && !hasExactLocaleVoice) {
      spoken = spoken.replace(/\bIkeja\b/gi, "Ee-keh-jah");
    }

    return spoken;
  }

  function speak(
    text: string,
    language: "en-NG" | "yo-NG" = voiceLanguage,
    onDone?: () => void
  ) {
    if (!("speechSynthesis" in window)) {
      onDone?.();
      return;
    }

    const synth = window.speechSynthesis;
    synth.cancel();

    const voices = synth.getVoices();
    const exact = voices.filter((voice) => voice.lang.toLowerCase() === language.toLowerCase());
    const sameLanguage = voices.filter((voice) =>
      voice.lang.toLowerCase().startsWith(language.slice(0, 2).toLowerCase())
    );
    const englishFallback = voices.filter((voice) => voice.lang.toLowerCase().startsWith("en"));
    const candidates =
      exact.length > 0 ? exact : sameLanguage.length > 0 ? sameLanguage : englishFallback;

    const utterance = new SpeechSynthesisUtterance(
      speechSafeText(text, language, exact.length > 0)
    );
    utterance.lang = language;
    utterance.rate = 0.98;
    utterance.pitch = 1;

    if (candidates.length > 0) {
      utterance.voice = candidates[voiceRotation % candidates.length];
      setVoiceRotation((current) => current + 1);
    }

    setVoiceState("speaking");
    utterance.onend = () => {
      if (!conversationActiveRef.current) setVoiceState("ready");
      onDone?.();
    };
    utterance.onerror = () => {
      if (!conversationActiveRef.current) setVoiceState("ready");
      onDone?.();
    };
    synth.speak(utterance);
  }

  function welcomeMessage(language: "en-NG" | "yo-NG") {
    if (language === "yo-NG") {
      return "Ẹ kú àbọ̀ sí Ikeja City Mall. Èmi ni ENESKO, olùrànlọ́wọ́ rẹ ní inú mall. Mo lè ràn ọ́ lọ́wọ́ láti rí ṣọ́ọ̀bù, tọ́ ọ́nà, ṣàyẹ̀wò ibi ìdákọ̀ ọkọ àti sinimá, tàbí bá ẹ so pọ̀ mọ́ iṣẹ́ mall. Kí ni mo lè ṣe fún ọ lónìí?";
    }
    return "Welcome to Ikeja City Mall. I’m ENESKO, your mall concierge. I can help you find stores, navigate the mall, check parking and cinema information, or connect you to mall operations. How can I help you today?";
  }

  function announceWelcome(language: "en-NG" | "yo-NG") {
    const greeting = welcomeMessage(language);
    setVoiceMessages([{ role: "assistant", text: greeting }]);
    speak(greeting, language);
  }

  function chooseVoiceLanguage(language: "en-NG" | "yo-NG") {
    setVoiceLanguage(language);
    if (
      voiceMessages.length === 0 ||
      (voiceMessages.length === 1 && voiceMessages[0].role === "assistant")
    ) {
      announceWelcome(language);
    }
  }

  async function ensureVoiceSession() {
    if (voiceSessionRef) return voiceSessionRef;

    const response = await fetch(API + "/api/v1/voice/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        direction: "INBOUND",
        provider: "BROWSER_SPEECH",
      }),
    });
    const body = await readJson(response, "Voice session");
    setVoiceSessionRef(body.session_ref);
    return body.session_ref as string;
  }

  async function sendVoiceTurn(text: string) {
    const clean = text.trim();
    if (!clean) return;

    setVoiceState("thinking");
    setNotice("");
    setVoiceMessages((current) => [...current, { role: "user", text: clean }]);
    setVoiceInput("");

    try {
      const ref = await ensureVoiceSession();
      const response = await fetch(
        API + `/api/v1/voice/sessions/${encodeURIComponent(ref)}/turn`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: clean }),
        }
      );
      const body = await readJson(response, "Voice concierge");
      const reply = body.answer || "I could not produce a response.";
      const responseLanguage: "en-NG" | "yo-NG" =
        body.language === "yo-NG" ? "yo-NG" : "en-NG";
      setVoiceLanguage(responseLanguage);
      setVoiceMessages((current) => [...current, { role: "assistant", text: reply }]);
      speak(reply, responseLanguage, () => {
        if (conversationActiveRef.current) {
          void beginListening(true);
        } else {
          setVoiceState("ready");
        }
      });
    } catch (error) {
      setVoiceState("ready");
      setNotice(error instanceof Error ? error.message : "Voice concierge is unavailable.");
    }
  }

  async function beginListening(autoRestart = false) {
    setNotice("");

    if (!window.isSecureContext) {
      conversationActiveRef.current = false;
      setConversationActive(false);
      setVoiceState("paused");
      setNotice(
        "Voice needs the secure HTTPS ENESKO address. This page will not open another QR automatically; use the single secure QR shown on the laptop."
      );
      return;
    }

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      conversationActiveRef.current = false;
      setConversationActive(false);
      setSpeechSupported(false);
      setVoiceState("paused");
      setNotice(
        "Speech recognition is not supported by this browser. Try current Chrome on Android, or use the text box."
      );
      return;
    }

    if (!navigator.mediaDevices?.getUserMedia) {
      conversationActiveRef.current = false;
      setConversationActive(false);
      setVoiceState("paused");
      setNotice("This browser cannot access a microphone in the current context. Use the secure HTTPS ENESKO address.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
      setVoicePermission("granted");
    } catch (error: any) {
      conversationActiveRef.current = false;
      setConversationActive(false);
      setVoicePermission("denied");
      setVoiceState("paused");
      const name = error?.name || "";
      if (name === "NotAllowedError" || name === "SecurityError") {
        setNotice("Microphone permission is blocked. Allow microphone access for ENESKO, then resume the conversation.");
      } else if (name === "NotFoundError") {
        setNotice("No usable microphone was found on this device.");
      } else {
        setNotice("ENESKO could not access this device's microphone. You can still type your request.");
      }
      return;
    }

    setSpeechSupported(true);
    const recognition = new SpeechRecognition();
    recognitionRef.current = recognition;
    recognition.lang = voiceLanguage;
    recognition.interimResults = false;
    recognition.continuous = false;

    let receivedResult = false;
    recognition.onstart = () => setVoiceState("listening");
    recognition.onerror = (event: any) => {
      const code = event?.error || "unknown";
      conversationActiveRef.current = false;
      setConversationActive(false);
      setVoiceState("paused");
      if (code === "no-speech") {
        setNotice("Conversation paused because no speech was detected. Tap Resume when you are ready.");
      } else if (code === "not-allowed" || code === "service-not-allowed") {
        setVoicePermission("denied");
        setNotice("Microphone or speech recognition permission is blocked for this site.");
      } else if (code === "audio-capture") {
        setNotice("The browser could not capture audio from this microphone.");
      } else if (code === "network") {
        setNotice("The browser speech service could not connect. Type your request or resume when internet access is stable.");
      } else {
        setNotice(`Speech recognition stopped (${code}). Resume when you are ready.`);
      }
    };
    recognition.onend = () => {
      recognitionRef.current = null;
      setVoiceState((current) => {
        if (current === "thinking" || current === "speaking" || current === "paused") return current;
        if (receivedResult) return "thinking";
        return conversationActiveRef.current ? "ready" : "paused";
      });
    };
    recognition.onresult = (event: any) => {
      receivedResult = true;
      const transcript = event.results?.[0]?.[0]?.transcript || "";
      if (transcript) void sendVoiceTurn(transcript);
    };

    try {
      recognition.start();
    } catch {
      if (!autoRestart) {
        conversationActiveRef.current = false;
        setConversationActive(false);
      }
      setVoiceState("paused");
      setNotice("Voice recognition could not start. Tap Resume to try again.");
    }
  }

  async function startVoiceConversation() {
    conversationActiveRef.current = true;
    setConversationActive(true);
    await ensureVoiceSession();
    await beginListening();
  }

  function pauseVoiceConversation() {
    conversationActiveRef.current = false;
    setConversationActive(false);
    recognitionRef.current?.abort?.();
    recognitionRef.current = null;
    window.speechSynthesis?.cancel();
    setVoiceState("paused");
  }

  async function endVoiceSession() {
    conversationActiveRef.current = false;
    setConversationActive(false);
    recognitionRef.current?.abort?.();
    recognitionRef.current = null;
    window.speechSynthesis?.cancel();

    if (voiceSessionRef) {
      try {
        await fetch(
          API + `/api/v1/voice/sessions/${encodeURIComponent(voiceSessionRef)}/complete`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({}),
          }
        );
      } finally {
        setVoiceSessionRef("");
      }
    }

    setVoiceInput("");
    setVoiceState("ready");
    setNotice("Conversation ended. The transcript stays visible; starting again creates a fresh live session.");
  }

  async function loadStores(search = "") {
    setLoading(true);
    setNotice("");
    try {
      const suffix = search.trim() ? `?q=${encodeURIComponent(search.trim())}` : "";
      const response = await fetch(API + "/api/v1/stores" + suffix);
      setStores(await readJson(response, "Store directory"));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Store directory is unavailable.");
    } finally {
      setLoading(false);
    }
  }

  async function loadCinema() {
    setLoading(true);
    setNotice("");
    try {
      const [statusResponse, showsResponse] = await Promise.all([
        fetch(API + "/api/v1/cinema/integration-status"),
        fetch(API + "/api/v1/cinema/shows"),
      ]);
      setCinema(await readJson(statusResponse, "Cinema information"));
      setShows(await readJson(showsResponse, "Cinema shows"));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Cinema information is unavailable.");
    } finally {
      setLoading(false);
    }
  }

  async function loadParking() {
    setLoading(true);
    setNotice("");
    try {
      const response = await fetch(API + "/api/v1/parking");
      setParking(await readJson(response, "Parking information"));
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Parking information is unavailable.");
    } finally {
      setLoading(false);
    }
  }

  async function loadRoute(toNode = "ICM-SAMSUNG", destination = "Samsung Experience Store") {
    setLoading(true);
    setNotice("");
    setRoute(null);
    setRouteDestination(destination);

    try {
      const params = new URLSearchParams({
        from_node: "ICM-ENTRANCE-2",
        to_node: toNode,
        accessible_only: "true",
      });
      const response = await fetch(API + "/api/v1/navigation/route?" + params.toString());
      setRoute(await readJson(response, "Indoor route"));
      setSection("navigate");
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "This destination has not yet been mapped for indoor navigation."
      );
      setSection("navigate");
    } finally {
      setLoading(false);
    }
  }

  async function openSection(next: Section) {
    setSection(next);
    setNotice("");
    setCaseRef("");

    if (next === "voice") {
      setVoiceState("ready");
      if (voiceMessages.length === 0) {
        announceWelcome(voiceLanguage);
      }
    }
    if (next === "stores" && stores.length === 0) await loadStores();
    if (next === "cinema" && !cinema) await loadCinema();
    if (next === "parking") await loadParking();
    if (next === "navigate" && !route) await loadRoute();
  }

  async function submitSupport(event: FormEvent) {
    event.preventDefault();
    if (!supportMessage.trim()) {
      setNotice("Tell mall operations what you need help with.");
      return;
    }

    setLoading(true);
    setNotice("");
    try {
      const response = await fetch(API + "/api/v1/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_type: "CUSTOMER_ASSISTANCE",
          summary: "Customer assistance request",
          description: supportMessage.trim(),
          contact: supportContact.trim() || null,
          channel: "web",
          priority: "NORMAL",
        }),
      });
      const body = await readJson(response, "Support request");
      setCaseRef(body.reference);
      setSupportMessage("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Support request could not be created.");
    } finally {
      setLoading(false);
    }
  }

  async function submitLostFound(event: FormEvent) {
    event.preventDefault();
    if (!lostItem.trim() || !lostLocation.trim()) {
      setNotice("Add the lost item and the last place you remember seeing it.");
      return;
    }

    setLoading(true);
    setNotice("");
    try {
      const response = await fetch(API + "/api/v1/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          case_type: "LOST_FOUND",
          summary: `Lost item: ${lostItem.trim()}`,
          description: `Lost item report for ${lostItem.trim()}.`,
          contact: lostContact.trim() || null,
          item_description: lostItem.trim(),
          last_seen_location: lostLocation.trim(),
          distinguishing_features: lostFeatures.trim() || null,
          channel: "web",
          priority: "NORMAL",
        }),
      });
      const body = await readJson(response, "Lost and found request");
      setCaseRef(body.reference);
      setLostItem("");
      setLostLocation("");
      setLostFeatures("");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Lost and found case could not be created.");
    } finally {
      setLoading(false);
    }
  }

  function parkingDisplay(item: ParkingItem) {
    const fresh =
      item.data_status === "STAFF_VERIFIED" &&
      item.expires_at &&
      new Date(item.expires_at).getTime() > Date.now();

    return {
      live: Boolean(fresh),
      label: fresh ? item.occupancy_status.replaceAll("_", " ") : "LIVE STATUS UNAVAILABLE",
    };
  }

  const secureShareReady = shareOrigin.startsWith("https://");

  return (
    <div className="appShell">
      <header className="topbar">
        <button className="brandButton" onClick={() => setSection("home")} type="button">
          <span className="brandMark">E</span>
          <span>
            <strong>ENESKO</strong>
            <small>Ikeja City Mall</small>
          </span>
        </button>

        <div className="topActions">
          <span className="verifiedPill">Official public sources + staff-verified operations</span>
          <button
            className="themeToggle"
            type="button"
            onClick={() => setPhoneAccessOpen(true)}
            aria-label="Open ENESKO on a phone"
          >
            Phone / QR
          </button>
          <button
            className="themeToggle"
            type="button"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label="Toggle light and dark mode"
          >
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </div>
      </header>

      <main className="main">
        {section !== "home" && (
          <button className="backButton" type="button" onClick={() => setSection("home")}>
            ← Back to home
          </button>
        )}

        {section === "home" && (
          <>
            <section className="hero">
              <div className="heroCopy">
                <span className="eyebrow">Your mall, intelligently connected</span>
                <h1>Find it. Reach it. Resolve it.</h1>
                <p>
                  One calm interface for discovery, indoor guidance, parking, cinema,
                  lost items and direct access to mall operations.
                </p>

                <form className="askBar" onSubmit={ask}>
                  <input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Ask: Where can I buy sports shoes?"
                    aria-label="Ask ENESKO"
                  />
                  <button type="submit" disabled={loading}>
                    {loading ? "Thinking..." : "Ask ENESKO"}
                  </button>
                </form>

                <div className="trustRow">
                  <span>Verified sources</span>
                  <span>Fresh operational status</span>
                  <span>No invented live data</span>
                </div>
              </div>

              <div className="heroVisual" aria-hidden="true">
                <div className="orbit orbitOne" />
                <div className="orbit orbitTwo" />
                <div className="visualCard visualCardTop">
                  <span>Navigate</span>
                  <strong>Entrance 2 → Store</strong>
                </div>
                <div className="visualCard visualCardBottom">
                  <span>Operations</span>
                  <strong>Cases tracked end-to-end</strong>
                </div>
                <div className="visualCore">E</div>
              </div>
            </section>

            {(answer || assistantStores.length > 0) && (
              <section className="answerPanel">
                <span className="eyebrow">ENESKO response</span>
                <p>{answer}</p>
                {assistantStores.length > 0 && (
                  <div className="compactResults">
                    {assistantStores.map((store) => (
                      <button
                        key={store.id}
                        type="button"
                        className="resultChip"
                        onClick={() =>
                          store.map_node_code
                            ? loadRoute(store.map_node_code, store.name)
                            : openSection("stores")
                        }
                      >
                        {store.name}
                      </button>
                    ))}
                  </div>
                )}
              </section>
            )}

            <section className="actionSection">
              <div className="sectionHeading">
                <div>
                  <span className="eyebrow">Everything in one place</span>
                  <h2>What do you need?</h2>
                </div>
              </div>

              <div className="actionGrid">
                {actions.map((action, index) => (
                  <button
                    key={action.id}
                    className="actionCard"
                    type="button"
                    onClick={() => openSection(action.id)}
                  >
                    <span className="actionNumber">0{index + 1}</span>
                    <strong>{action.title}</strong>
                    <p>{action.copy}</p>
                    <span className="actionArrow">↗</span>
                  </button>
                ))}
              </div>
            </section>
          </>
        )}

        {section === "voice" && (
          <section className="contentSection voiceSection">
            <div className="voiceHero">
              <div>
                <span className="eyebrow">ENESKO Voice</span>
                <h1>Talk to the mall.</h1>
                <p>
                  Ask for a store, parking status, cinema information, indoor directions,
                  lost-and-found help or a human handoff. ENESKO uses the same verified
                  operational sources as the rest of the platform.
                </p>
              </div>
              <span className="neutralBadge">
                {typeof window !== "undefined" && !window.isSecureContext
                  ? "HTTPS required for phone mic"
                  : speechSupported
                    ? voicePermission === "granted"
                      ? "Microphone ready"
                      : "Browser voice + ENESKO tools"
                    : "Text fallback available"}
              </span>
            </div>

            <div className="voiceLanguageSwitch" aria-label="Voice language">
              <span>Voice language</span>
              <button
                type="button"
                className={voiceLanguage === "en-NG" ? "active" : ""}
                onClick={() => chooseVoiceLanguage("en-NG")}
              >
                English
              </button>
              <button
                type="button"
                className={voiceLanguage === "yo-NG" ? "active" : ""}
                onClick={() => chooseVoiceLanguage("yo-NG")}
              >
                Yorùbá
              </button>
              <small>
                Typed Yorùbá is detected automatically. Choose Yorùbá before speaking for reliable speech recognition.
              </small>
            </div>

            <div className="voiceLayout">
              <div className="voiceConsole">
                <button
                  className={`voiceOrb voice-${voiceState}`}
                  type="button"
                  onClick={conversationActive ? pauseVoiceConversation : startVoiceConversation}
                  disabled={voiceState === "thinking" || voiceState === "speaking"}
                  aria-label={conversationActive ? "Pause ENESKO conversation" : "Start ENESKO conversation"}
                >
                  <span className="voicePulse" />
                  <strong>
                    {voiceState === "listening"
                      ? "Listening"
                      : voiceState === "thinking"
                        ? "Thinking"
                        : voiceState === "speaking"
                          ? "Speaking"
                          : conversationActive
                            ? "Pause"
                            : voiceState === "paused"
                              ? "Resume"
                              : "Start"}
                  </strong>
                  <small>
                    {conversationActive
                      ? "Conversation stays open"
                      : voiceState === "paused"
                        ? "Tap to continue"
                        : "One tap starts the chamber"}
                  </small>
                </button>

                <div className="voiceHints">
                  <button type="button" onClick={() => sendVoiceTurn("Where can I buy sports shoes?")}>
                    Find sports shoes
                  </button>
                  <button type="button" onClick={() => sendVoiceTurn("What is the parking status right now?")}>
                    Check parking
                  </button>
                  <button type="button" onClick={() => sendVoiceTurn("What movies are showing?")}>
                    Ask about cinema
                  </button>
                </div>

                <div className="desktopVoiceQr">
                  <span className="eyebrow">One QR for every phone</span>
                  {secureShareReady ? (
                    <>
                      <div className="desktopQrFrame">
                        <img
                          src={`${API}/api/v1/access/qr.svg?url=${encodeURIComponent(shareOrigin)}`}
                          alt="Secure ENESKO mobile access QR code"
                        />
                      </div>
                      <small>Scan this same secure QR on any customer phone.</small>
                    </>
                  ) : (
                    <small>
                      Open ENESKO through its HTTPS address, or configure NEXT_PUBLIC_PUBLIC_APP_URL,
                      and the single secure phone QR will appear here.
                    </small>
                  )}
                </div>
              </div>

              <div className="voiceConversation">
                <div className="voiceConversationHeader">
                  <div>
                    <span className="eyebrow">Conversation</span>
                    <h2>Live concierge</h2>
                  </div>
                  {voiceMessages.length > 0 && (
                    <div className="voiceSessionActions">
                      <button
                        className="secondaryAction"
                        type="button"
                        onClick={conversationActive ? pauseVoiceConversation : startVoiceConversation}
                        disabled={voiceState === "thinking" || voiceState === "speaking"}
                      >
                        {conversationActive ? "Pause" : "Resume"}
                      </button>
                      <button className="secondaryAction" type="button" onClick={endVoiceSession}>
                        End conversation
                      </button>
                    </div>
                  )}
                </div>

                <div className="voiceMessages">
                  {voiceMessages.length ? (
                    voiceMessages.map((message, index) => (
                      <article className={`voiceMessage ${message.role}`} key={index}>
                        <span>{message.role === "user" ? "You" : "ENESKO"}</span>
                        <p>{message.text}</p>
                      </article>
                    ))
                  ) : (
                    <div className="emptyState voiceEmpty">
                      <strong>Ready when you are.</strong>
                      <p>Start once, then speak naturally. ENESKO keeps the active session context and listens again after each spoken response.</p>
                    </div>
                  )}
                </div>

                <form
                  className="voiceComposer"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void sendVoiceTurn(voiceInput);
                  }}
                >
                  <input
                    value={voiceInput}
                    onChange={(event) => setVoiceInput(event.target.value)}
                    placeholder="Type if you prefer not to speak..."
                    aria-label="Voice concierge text fallback"
                  />
                  <button type="submit" disabled={voiceState === "thinking" || !voiceInput.trim()}>
                    Send
                  </button>
                </form>
              </div>
            </div>
          </section>
        )}

        {section === "stores" && (
          <section className="contentSection">
            <div className="sectionHeading">
              <div>
                <span className="eyebrow">Directory</span>
                <h1>Find a store</h1>
                <p>Current public listings are sourced from official mall or brand directories.</p>
              </div>
            </div>

            <form
              className="inlineSearch"
              onSubmit={(event) => {
                event.preventDefault();
                loadStores(query);
              }}
            >
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search sports, phones, shoes..."
              />
              <button type="submit">Search</button>
            </form>

            <div className="storeGrid">
              {stores.map((store) => (
                <article className="storeCard" key={store.id}>
                  <div className="storeTopline">
                    <span>{store.categories.map((category) => category.name).join(" · ")}</span>
                    <span className={store.data_status === "PUBLIC_VERIFIED" ? "sourceDot" : "neutralBadge"}>
                      {store.data_status === "PUBLIC_VERIFIED" ? "Verified source" : "Public reference"}
                    </span>
                  </div>
                  <h3>{store.name}</h3>
                  <p>{store.description}</p>
                  {store.unit && <small>Unit: {store.unit}</small>}
                  {store.nearest_landmark && <small>Location hint: {store.nearest_landmark}</small>}
                  {store.opening_hours && <small>{store.opening_hours}</small>}
                  {store.public_rating !== null && (
                    <small>
                      Public rating reference: {store.public_rating.toFixed(1)}
                      {store.public_review_count ? ` · ${store.public_review_count} reviews` : ""}
                    </small>
                  )}
                  <small>
                    Evidence: {store.verification_confidence.toLowerCase()} confidence · {store.location_confidence.replaceAll("_", " ").toLowerCase()}
                  </small>
                  <div className="storeFooter">
                    <small>{store.source_name}</small>
                    {store.map_node_code ? (
                      <button
                        type="button"
                        onClick={() => loadRoute(store.map_node_code as string, store.name)}
                      >
                        Navigate
                      </button>
                    ) : (
                      <span className="mapPending">Indoor map pending</span>
                    )}
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}

        {section === "cinema" && (
          <section className="contentSection">
            <div className="featureHero">
              <div>
                <span className="eyebrow">Cinema</span>
                <h1>{cinema?.cinema_name || "Silverbird Cinemas, Ikeja City Mall"}</h1>
                <p>
                  ENESKO uses official cinema information and will not freeze temporary showtimes
                  into the app as if they were live.
                </p>
              </div>
              <div className="featureStats">
                <div><span>Box office</span><strong>{cinema?.box_office_hours || "10:00-22:00 daily"}</strong></div>
                <div><span>Movie enquiry</span><strong>{cinema?.movie_enquiry || "+234 902 606 7603"}</strong></div>
              </div>
            </div>

            {shows.length > 0 ? (
              <div className="storeGrid">
                {shows.map((show) => (
                  <article className="storeCard" key={show.id}>
                    <h3>{show.movie_title}</h3>
                    <p>{show.show_time}</p>
                  </article>
                ))}
              </div>
            ) : (
              <div className="emptyState">
                <strong>Live ENESKO cinema feed is not connected yet.</strong>
                <p>
                  Until the official adapter is authorized, use Silverbird's live service for
                  current showtimes and booking.
                </p>
                <a
                  className="primaryLink"
                  href={cinema?.official_booking_url || "https://silverbirdcinemas.com/cinema/ikeja/"}
                  target="_blank"
                  rel="noreferrer"
                >
                  Open official cinema service ↗
                </a>
              </div>
            )}
          </section>
        )}

        {section === "parking" && (
          <section className="contentSection">
            <div className="sectionHeading">
              <div>
                <span className="eyebrow">Parking</span>
                <h1>Arrive with less uncertainty</h1>
                <p>Ikeja City Mall publicly states that it provides more than 700 parking bays.</p>
              </div>
              <button className="secondaryAction" type="button" onClick={loadParking}>
                Refresh status
              </button>
            </div>

            <div className="parkingGrid">
              {parking.map((item) => {
                const display = parkingDisplay(item);
                return (
                  <article className="parkingCard" key={item.id}>
                    <div>
                      <span className={display.live ? "liveBadge" : "neutralBadge"}>
                        {display.live ? "Staff verified" : "Capacity information"}
                      </span>
                      <h2>{item.name}</h2>
                      <p className="parkingStatus">{display.label}</p>
                    </div>
                    <div className="parkingMeta">
                      <div><span>Published capacity</span><strong>700+ bays</strong></div>
                      <div>
                        <span>Live freshness</span>
                        <strong>
                          {display.live && item.expires_at
                            ? `Valid until ${new Date(item.expires_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
                            : "Awaiting fresh staff/integration update"}
                        </strong>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>
        )}

        {section === "navigate" && (
          <section className="contentSection">
            <div className="sectionHeading">
              <div>
                <span className="eyebrow">Indoor navigation</span>
                <h1>Mini mall navigation</h1>
                <p>
                  Start from Entrance 2 and follow ENESKO to a mapped destination. The current
                  geometry is a pre-launch reference model until the authorized mall floor plan is connected.
                </p>
              </div>
            </div>

            <div className="navigationLayout">
              <div className="miniMap">
                <div className="mapPath" />
                <div className="mapNode startNode"><span>You</span><strong>Entrance 2</strong></div>
                <div className="mapNode midNode"><span>Pass</span><strong>Main concourse</strong></div>
                <div className="mapNode endNode"><span>Destination</span><strong>{routeDestination}</strong></div>
              </div>

              <div className="routePanel">
                <span className="neutralBadge">Reference route model</span>
                <h2>{routeDestination}</h2>
                {route ? (
                  <>
                    <p className="routeDistance">Route model: {route.total_distance_m} m</p>
                    <ol>
                      {route.steps.map((step, index) => (
                        <li key={index}>{step.instruction}</li>
                      ))}
                    </ol>
                    <p className="finePrint">
                      Exact turn geometry and distance will be replaced by authorized ICM indoor-map data.
                    </p>
                  </>
                ) : (
                  <p>Loading the mapped route…</p>
                )}
              </div>
            </div>
          </section>
        )}

        {section === "lost" && (
          <section className="contentSection formSection">
            <span className="eyebrow">Lost & Found</span>
            <h1>Create a trackable report</h1>
            <p>
              ENESKO structures the report and gives you a case reference. Mall staff still verify
              matches and authorize any item release.
            </p>

            <form className="productForm" onSubmit={submitLostFound}>
              <label>
                What did you lose?
                <input value={lostItem} onChange={(event) => setLostItem(event.target.value)} placeholder="Black wallet" />
              </label>
              <label>
                Last place you remember seeing it
                <input value={lostLocation} onChange={(event) => setLostLocation(event.target.value)} placeholder="Food court" />
              </label>
              <label>
                Distinguishing features
                <textarea value={lostFeatures} onChange={(event) => setLostFeatures(event.target.value)} placeholder="Brand, colour, marks, contents..." />
              </label>
              <label>
                Contact
                <input value={lostContact} onChange={(event) => setLostContact(event.target.value)} placeholder="Phone or email" />
              </label>
              <button type="submit" disabled={loading}>Create lost-item case</button>
            </form>
          </section>
        )}

        {section === "help" && (
          <section className="contentSection formSection">
            <span className="eyebrow">Mall operations</span>
            <h1>Get human help</h1>
            <p>Send a request into ENESKO OPS so it can be tracked instead of disappearing into a call or chat.</p>

            <form className="productForm" onSubmit={submitSupport}>
              <label>
                What do you need help with?
                <textarea value={supportMessage} onChange={(event) => setSupportMessage(event.target.value)} placeholder="Describe the issue or request..." />
              </label>
              <label>
                Contact
                <input value={supportContact} onChange={(event) => setSupportContact(event.target.value)} placeholder="Phone or email (optional)" />
              </label>
              <button type="submit" disabled={loading}>Send to mall operations</button>
            </form>
          </section>
        )}

        {phoneAccessOpen && (
          <div className="phoneAccessBackdrop" role="presentation" onClick={() => setPhoneAccessOpen(false)}>
            <section
              className="phoneAccessModal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="phone-access-title"
              onClick={(event) => event.stopPropagation()}
            >
              <button
                className="phoneAccessClose"
                type="button"
                onClick={() => setPhoneAccessOpen(false)}
                aria-label="Close phone access"
              >
                ×
              </button>
              <span className="eyebrow">Open ENESKO on your phone</span>
              <h2 id="phone-access-title">Scan and continue on mobile</h2>
              <p>
                Multiple phones can use the same ENESKO address. For microphone access on phones,
                use an HTTPS address rather than a plain local-IP HTTP address.
              </p>

              {shareOrigin && secureShareReady ? (
                <>
                  <div className="qrFrame">
                    <img
                      src={`${API}/api/v1/access/qr.svg?url=${encodeURIComponent(shareOrigin)}`}
                      alt="QR code for the secure ENESKO customer address"
                    />
                  </div>
                  <code className="shareUrl">{shareOrigin}</code>
                  <div className="buttonRow phoneButtons">
                    <button
                      className="secondaryAction"
                      type="button"
                      onClick={() => navigator.clipboard?.writeText(shareOrigin)}
                    >
                      Copy secure link
                    </button>
                  </div>
                </>
              ) : (
                <p className="finePrint">
                  A secure phone QR is not available from this HTTP address. Open ENESKO through HTTPS or configure NEXT_PUBLIC_PUBLIC_APP_URL.
                </p>
              )}

              <p className="finePrint">
                {typeof window !== "undefined" && window.isSecureContext
                  ? "Secure context detected. Compatible browsers can request microphone permission."
                  : "This current address is not a secure context. Browsing and typed ENESKO requests can still work, but phone microphone access may be blocked."}
              </p>
            </section>
          </div>
        )}

        {caseRef && (
          <div className="caseToast">
            <span>Request created</span>
            <strong>{caseRef}</strong>
            <button type="button" onClick={() => setCaseRef("")}>×</button>
          </div>
        )}

        {notice && (
          <div className="noticeBar">
            <span>{notice}</span>
            <button type="button" onClick={() => setNotice("")}>×</button>
          </div>
        )}
      </main>
    </div>
  );
}
