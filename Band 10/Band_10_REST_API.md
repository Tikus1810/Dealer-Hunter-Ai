---
document_id: BAND-10
status: Draft
title: Deal Hunter AI - REST API
version: 2
---

# REST API Specification

## Objective

Provide a versioned, secure and well-documented REST API.

## Standards

-   Base path: /api/v1
-   JSON request/response
-   OpenAPI generation
-   UUID identifiers
-   Consistent error model
-   Cursor or page-based pagination

## Resource Groups

-   Authentication
-   Users
-   Search Profiles
-   Offers
-   DealBrain
-   RepairBrain
-   Favorites
-   Notifications
-   Administration

## Cross-Cutting Requirements

-   JWT authentication
-   Input validation
-   Rate limiting support
-   Idempotent endpoints where applicable
-   Structured logging
-   Request correlation IDs

## Error Model

Every error returns: - code - message - details - correlation_id

## Deliverables

-   OpenAPI specification
-   DTO definitions
-   Endpoint contracts
-   API versioning strategy
