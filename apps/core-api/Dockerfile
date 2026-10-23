# MCore core-api — Rust multi-stage build
FROM rust:slim AS builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo build --release --locked

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates libssl3 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1000 appuser
COPY --from=builder /app/target/release/mcore-core-api /usr/local/bin/mcore-core-api
USER appuser
EXPOSE 8080
CMD ["mcore-core-api"]
