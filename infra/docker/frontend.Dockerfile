# =============================================================================
# Kairos Frontend Dockerfile — Multi-stage Next.js Standalone Build
# =============================================================================
# Three-stage build: deps → builder → runner.
# Produces a minimal Alpine image running the Next.js standalone server.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Dependencies — install node_modules with deterministic lockfile
# ---------------------------------------------------------------------------
FROM node:22-alpine AS deps

WORKDIR /app

# Copy package manifests only (layer cache optimisation).
COPY frontend/package.json frontend/package-lock.json* ./

# Install production dependencies only.
RUN npm ci --only=production

# ---------------------------------------------------------------------------
# Stage 2: Builder — compile the Next.js application
# ---------------------------------------------------------------------------
FROM node:22-alpine AS builder

WORKDIR /app

# Bring in all dependencies (including devDependencies for the build).
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .

# Build the Next.js app (output: standalone mode must be enabled in next.config).
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 3: Runner — minimal production image
# ---------------------------------------------------------------------------
FROM node:22-alpine AS runner

WORKDIR /app

# Force production mode.
ENV NODE_ENV=production

# --- Security: create a dedicated non-root user/group ---
RUN addgroup -g 1001 -S kairos && adduser -S kairos -u 1001

# Copy only the artifacts needed at runtime.
COPY --from=builder /app/public ./public
COPY --from=builder --chown=kairos:kairos /app/.next/standalone ./
COPY --from=builder --chown=kairos:kairos /app/.next/static ./.next/static

# Switch to non-root user.
USER kairos

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

# Start the standalone Next.js server.
CMD ["node", "server.js"]
