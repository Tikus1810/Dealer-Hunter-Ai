---
document_id: BAND-05
status: Draft
title: Deal Hunter AI - DealBrain AI
version: 2
---

# DealBrain AI Specification

## Objective

DealBrain is the central decision engine that evaluates technology
offers and produces transparent recommendations.

## Inputs

-   Offer metadata
-   Public seller information
-   Device specifications
-   Estimated market value
-   Repair assessment
-   Historical price data (when available)

## Outputs

-   Deal Score (0-100)
-   Confidence Score
-   Estimated Market Value
-   Estimated Total Cost
-   Recommendation
-   Human-readable explanation

## Scoring Principles

The score must be explainable and deterministic for identical inputs.

Primary factors: - Price competitiveness - Device condition - Repair
feasibility - Seller confidence - Completeness of listing - Risk
indicators

## Architecture

Modules: - Price Analyzer - Seller Analyzer - Specification Analyzer -
Risk Analyzer - Scoring Engine - Explanation Generator

Each module must expose interfaces and remain independently testable.

## Requirements

-   No hidden scoring rules.
-   Every score includes an explanation.
-   Unknown values reduce confidence, not correctness.
-   Scores are versioned for future improvements.

## Deliverables

-   DealBrain service interfaces
-   Scoring contracts
-   Domain models
-   Test strategy
