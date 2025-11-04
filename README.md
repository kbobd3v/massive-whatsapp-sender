# Evolution API: Massive Whatsapp Sender

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)![Docker](https://img.shields.io/badge/Docker-20.10%2B-blue?style=for-the-badge&logo=docker)![Shell](https://img.shields.io/badge/Shell-Bash-lightgrey?style=for-the-badge&logo=gnu-bash)

A robust, production-ready system engineered to send bulk sequential messages (Text + Video) via the Evolution API.

## Core Architecture Principles

This system was built on a foundation of professional DevOps principles, not shortcuts.

*   📦 **Dockerized Environment:** The entire backend stack (API, Database, Cache) is fully containerized with Docker Compose for perfect isolation and reproducibility.
*   🧹 **Data Sanitization Pipeline:** Includes a dedicated tool to clean and restore severely malformed CSV data into a standard, reliable format. We don't trust dirty data.
*   🚀 **Robust Sending Script:** The Python sender is engineered for resilience, with human-like delays to minimize blocking risk, clear error handling, and a sequential sending flow.
*   🔑 **Strict Configuration Management:** A hard separation between code, configuration, and secrets (`.gitignore`, `.env`, `.secrets.env`) ensures the system is secure and portable.

---

## Technology Stack

*   **Backend:** Docker, Docker Compose
*   **Services:**
    *   `evoapicloud/evolution-api`: The WhatsApp API Gateway.
    *   `postgres:16-alpine`: The primary database.
    *   `redis:6-alpine`: The cache and session store.
*   **Automation:**
    *   `Python 3`: For the core sending and data cleaning logic.
    *   `ffmpeg`: For professional-grade media transcoding.

---

## Setup & Installation

Follow these steps precisely. Do not skip any.

### 1. Prerequisites

Ensure you have the following tools installed on your system:
*   `git`
*   `docker` & `docker-compose`
*   `python3` & `pip`
*   `ffmpeg`

### 2. Clone the Repository

```bash
git clone git@github.com:kbobd3v/massive-whatsapp-sender.git
cd massive