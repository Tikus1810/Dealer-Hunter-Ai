---
document_id: BAND-01
language: Mixed (English technical terms, German explanations)
status: Draft
title: Deal Hunter AI - Master PRD
version: 2
---

# Deal Hunter AI -- Master PRD

## Executive Summary

Deal Hunter AI is a production-grade AI platform that discovers,
evaluates and prioritizes second-hand technology deals.

Primary categories: - Windows Laptops - MacBooks - iPhones - Game
Consoles

The system shall provide: - Explainable Deal Score - Repair analysis -
Economic analysis - Replacement part recommendations - Saved searches -
Push notifications

------------------------------------------------------------------------

# Product Vision

Mission:

Build the most trustworthy AI assistant for evaluating used technology
offers.

Core Principles:

1.  Explainable AI
2.  Human decision remains final
3.  Modular Architecture
4.  API-first
5.  Security by Design
6.  Test-first Development

------------------------------------------------------------------------

# Scope (MVP)

Required:

-   Authentication
-   User Profiles
-   Saved Searches
-   DealBrain
-   RepairBrain
-   Favorites
-   Notifications
-   Flutter App
-   FastAPI Backend
-   PostgreSQL
-   Redis

Not included:

-   Automatic purchasing
-   Messaging sellers
-   Circumventing marketplace restrictions

------------------------------------------------------------------------

# Quality Standards

Architecture: - Clean Architecture - SOLID - Dependency Injection -
Repository Pattern - Domain Driven Design (lightweight)

Testing: - Unit Tests - Integration Tests - End-to-End Tests

Security: - JWT - Argon2 - HTTPS - Secret Management

Documentation: Every public module must be documented.

------------------------------------------------------------------------

# Acceptance Criteria

The product is considered MVP-ready only if:

-   All functional requirements implemented.
-   All acceptance tests pass.
-   API documented.
-   CI/CD green.
-   Docker deployment works.
-   No critical defects.

------------------------------------------------------------------------

# Next Document

Band_02_System_Architecture.md
