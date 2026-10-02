# ENESKO Learning Foundation

## Goal

ENESKO now has a governed learning foundation that follows this release path:

Customer interactions → anonymized/pseudonymous learning signals → pattern analysis → candidate model training → testing → human approval → active ENESKO pattern model.

This is intentionally not uncontrolled live self-training. A customer interaction can add a safe learning signal, but it cannot directly rewrite ENESKO behaviour.

## Privacy boundary

The learning dataset does not store raw customer message text, phone numbers, email addresses, Lost & Found descriptions, or the VoiceSession transcript.

It stores:
- channel;
- assistant intent;
- language;
- allowlisted topic tags;
- whether human help was needed;
- an HMAC-SHA256 pseudonymous session identifier when a session reference is available;
- timestamp.

Operational records remain separate. Existing Conversation, VoiceSession, case and channel-message records may retain the content required for operations and workflow continuity; those records are not copied into the learning dataset.

## Pattern model V1

The first trainable model is `ANONYMIZED_PATTERN_V1`.

It learns:
- topic frequency;
- topic co-occurrence;
- next-topic transitions inside pseudonymous sessions.

It can later suggest the most supported next related topic. It never changes verified mall facts, inventory truth, navigation geometry, parking truth, cinema truth or tenant records.

## Approval gate

A candidate cannot become active automatically.

Current gate:
- at least 10 anonymized interaction signals;
- candidate has been trained and marked TESTED;
- evaluation score must be at least 0.50;
- a PLATFORM_SUPER_ADMIN or MALL_ADMINISTRATOR must explicitly approve it.

Approving a new model retires the previous active approved pattern model.

## ENESKO OPS

Open **Learning** in ENESKO OPS to:
- see accumulated learning signals;
- see model versions;
- train a candidate;
- review its evaluation score;
- approve a tested candidate that passes the gate;
- see which model is active.

## API

Protected staff endpoints:
- `GET /api/v1/learning/status`
- `GET /api/v1/learning/models`
- `POST /api/v1/learning/train`
- `POST /api/v1/learning/models/{id}/approve`

## Conversation memory

VoiceSession working memory is separate from the learning dataset.

A live voice session can remember:
- the current shopping plan;
- the last intent/data;
- an active Lost & Found interview and its current stage;
- the resulting Lost & Found case reference.

This lets follow-ups such as `Which one first?`, `Remove food`, or the next answer in a Lost & Found interview continue inside the same session.

## Voice chamber

The Customer Web voice experience now uses a conversation loop:

LISTEN → PROCESS → SPEAK → LISTEN AGAIN.

The browser microphone is still controlled by browser security and browser SpeechRecognition support. Normal successful turns should no longer require a fresh tap after every ENESKO reply. Pause and End conversation remain explicit controls.

## Single phone QR

The Voice screen has one desktop-only secure QR area.

For a truly permanent customer QR, configure the Customer Web deployment with a stable HTTPS URL:

```env
NEXT_PUBLIC_PUBLIC_APP_URL=https://your-stable-enesko-domain.example
```

Every customer phone can scan that same QR.

During development, opening Customer Web through an HTTPS tunnel also produces one QR for that current tunnel URL. A random Quick Tunnel URL is temporary, so its QR is not permanent across tunnel restarts.

Plain LAN HTTP is intentionally not used as the microphone QR target. If a phone opens an insecure HTTP address, ENESKO shows a message instead of opening another QR and creating the previous QR loop.

## Future model upgrades

The approval pipeline is model-agnostic. A richer recommender, classifier, embedding model or conversational model can later use the same governance flow:

training data preparation → candidate → evaluation → approval → active release.

Operational truth must continue to come from verified ENESKO tools and approved data sources.
