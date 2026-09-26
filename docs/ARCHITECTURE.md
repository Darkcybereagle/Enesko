# Enesko Architecture

## Core rule

The language model/conversation layer is not a physical-world source of truth.

```
Web / Future Voice / WhatsApp / Email
                 |
                 v
       Conversation Orchestrator
                 |
        +--------+--------+
        |                 |
        v                 v
 Structured Tools     Human Handoff
        |
 +------+-------+
 |              |
Store Service  Knowledge Service
 |              |
 +------DB------+
```

## Source hierarchy

1. Authorized live integration
2. Verified synchronized source
3. Authorized staff update
4. Verified static knowledge
5. Human escalation

If none is available, Enesko must not fabricate an operational answer.

## Future integration boundary

Parking, cinema, voice, WhatsApp, email, indoor positioning and IoT will connect behind dedicated adapters rather than being embedded into conversational logic.
