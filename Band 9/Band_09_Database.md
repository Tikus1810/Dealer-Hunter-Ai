---
document_id: BAND-09
status: Draft
title: Deal Hunter AI - Database Design
version: 2
---

# Database Design

## Objective

Design a scalable relational database for all application domains.

## Core Entities

-   User
-   SearchProfile
-   Offer
-   Product
-   Category
-   Favorite
-   Notification
-   DealScore
-   RepairReport
-   SellerScore
-   PriceHistory

## Rules

-   UUID primary keys
-   created_at / updated_at timestamps
-   Soft delete where appropriate
-   Foreign key integrity
-   Indexed search fields
-   Migration-first workflow using Alembic

## Performance

-   Normalize transactional data.
-   Use indexes for frequent lookups.
-   Cache read-heavy queries through Redis.

## Deliverables

-   ER model
-   SQLAlchemy models
-   Alembic migrations
-   Seed data
