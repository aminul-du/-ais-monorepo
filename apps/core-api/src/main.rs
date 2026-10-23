//! MCore core-api — OSINT / high-perf telemetry entrypoint.
//!
//! Owner: Aminul Islam Shamim (AIS) — Meticulous Core Ltd.
//! Founder ID: MCORE-FDR-AIS-001

use axum::{routing::get, Json, Router};
use serde_json::{json, Value};
use std::net::SocketAddr;

mod traceroute;

async fn health() -> Json<Value> {
    Json(json!({
        "status": "ok",
        "service": "mcore-core-api",
        "version": env!("CARGO_PKG_VERSION"),
    }))
}

fn app() -> Router {
    Router::new()
        .route("/healthz", get(health))
        .merge(traceroute::router())
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "info".into()),
        )
        .init();

    let addr: SocketAddr = std::env::var("BIND_ADDR")
        .unwrap_or_else(|_| "0.0.0.0:8080".into())
        .parse()
        .expect("invalid BIND_ADDR");

    tracing::info!(%addr, "starting mcore-core-api");

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app()).await.unwrap();
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::{Request, StatusCode};
    use http_body_util::BodyExt;
    use tower::ServiceExt;

    #[tokio::test]
    async fn health_returns_ok() {
        let resp = app()
            .oneshot(Request::builder().uri("/healthz").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(resp.status(), StatusCode::OK);
        let bytes = resp.into_body().collect().await.unwrap().to_bytes();
        let v: Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(v["status"], "ok");
        assert_eq!(v["service"], "mcore-core-api");
    }
}
