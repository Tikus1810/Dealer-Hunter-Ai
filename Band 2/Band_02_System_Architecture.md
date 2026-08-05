---
document_id: BAND-02
status: Draft
title: Deal Hunter AI - System Architecture
version: 2
---

# System Architecture

## Goal

Define the target architecture for Deal Hunter AI using Clean
Architecture and modular boundaries.

## Technology Stack

Frontend: - Flutter - Dart

Backend: - Python 3.13 - FastAPI

Infrastructure: - PostgreSQL - Redis - Docker - GitHub Actions

## High-Level Components

-   Flutter Client
-   REST API
-   Authentication Service
-   Marketplace Provider Layer
-   DealBrain
-   RepairBrain
-   Notification Service
-   Persistence Layer

## Layering

Presentation → Application → Domain → Infrastructure

Business rules must only exist inside the Domain/Application layers.

## Module Boundaries

-   auth
-   users
-   offers
-   search
-   scoring
-   repair
-   notifications
-   analytics

Each module exposes public interfaces only.

## Marketplace Integration

Use a provider abstraction.

Required interfaces: - MarketplaceProvider - OfferNormalizer -
OfferRepository - SearchScheduler

No business logic may depend on a specific marketplace implementation.

## Non-Functional Requirements

-   Horizontal scalability
-   Testability
-   Replaceable providers
-   Observability
-   Security by design

## Deliverables

-   Architecture skeleton
-   Dependency graph
-   Module interfaces
-   Docker-ready structure
