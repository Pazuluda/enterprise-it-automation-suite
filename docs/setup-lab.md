# Enterprise IT Automation Suite - Lab Setup

## Lab utilise

- APP01 Debian : API FastAPI
- Windows Server : agent PowerShell
- Mode actuel : Simulation
- Domaine AD : non requis pour la simulation

## API

URL API :

http://10.10.10.11:8000

Documentation locale :

http://10.10.10.11:8000/docs-local

## Securite

Les routes sensibles demandent le header :

X-API-Key: <cle API>

La cle reelle est stockee dans :

/etc/eitas-api.env

Ce fichier ne doit jamais etre envoye sur GitHub.

## Workflow actuel

Creation demande
-> waiting_approval
-> validation admin
-> pending
-> agent Windows
-> processing
-> completed

## Routes principales

POST /api/onboarding/request
GET  /api/requests
GET  /api/agent/pending
POST /api/agent/claim/{request_id}
POST /api/agent/result/{request_id}
POST /api/admin/requests/{request_id}/approve
POST /api/admin/requests/{request_id}/reject
GET  /api/audit-logs
