//! MCore TCP traceroute — L4 detection, Cloud Run safe (no CAP_NET_RAW).
//!
//! Uses TCP SYN to a port (default 443) instead of ICMP, so it works
//! inside containers without privileged network access.
//!
//! Owner: Aminul Islam Shamim (AIS) — Meticulous Core Ltd.
//! Founder ID: MCORE-FDR-AIS-001

use axum::{extract::Json as AxumJson, http::StatusCode, response::IntoResponse, Json, Router};
use serde::{Deserialize, Serialize};
use std::time::{Duration, Instant};
use tokio::net::TcpStream;
use tokio::time::timeout;

#[derive(Debug, Deserialize)]
pub struct TraceRequest {
    pub target: String,
    #[serde(default = "default_port")]
    pub port: u16,
    #[serde(default = "default_timeout_ms")]
    pub timeout_ms: u64,
}

fn default_port() -> u16 { 443 }
fn default_timeout_ms() -> u64 { 1000 }

#[derive(Debug, Serialize)]
pub struct Hop {
    pub target: String,
    pub port: u16,
    pub reachable: bool,
    pub rtt_ms: Option<u64>,
    pub error: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct TraceResponse {
    pub hops: Vec<Hop>,
    pub total_ms: u64,
}

pub async fn trace(req: TraceRequest) -> Result<TraceResponse, String> {
    if req.target.trim().is_empty() {
        return Err("target is required".into());
    }
    if req.port == 0 {
        return Err("port must be 1-65535".into());
    }
    let start = Instant::now();
    let addr = format!("{}:{}", req.target, req.port);
    let dur = Duration::from_millis(req.timeout_ms.clamp(50, 10_000));
    let hop_start = Instant::now();
    let result = timeout(dur, TcpStream::connect(&addr)).await;
    let hop = match result {
        Ok(Ok(_stream)) => Hop {
            target: req.target.clone(),
            port: req.port,
            reachable: true,
            rtt_ms: Some(hop_start.elapsed().as_millis() as u64),
            error: None,
        },
        Ok(Err(e)) => Hop {
            target: req.target.clone(),
            port: req.port,
            reachable: false,
            rtt_ms: None,
            error: Some(e.to_string()),
        },
        Err(_) => Hop {
            target: req.target.clone(),
            port: req.port,
            reachable: false,
            rtt_ms: None,
            error: Some(format!("timeout after {}ms", req.timeout_ms)),
        },
    };
    Ok(TraceResponse { hops: vec![hop], total_ms: start.elapsed().as_millis() as u64 })
}

pub async fn handler(AxumJson(req): AxumJson<TraceRequest>) -> impl IntoResponse {
    match trace(req).await {
        Ok(resp) => (StatusCode::OK, Json(serde_json::json!(resp))),
        Err(e) => (StatusCode::BAD_REQUEST, Json(serde_json::json!({"error": e}))),
    }
}

pub fn router() -> Router {
    Router::new().route("/traceroute", axum::routing::post(handler))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn empty_target_rejected() {
        let r = trace(TraceRequest { target: "".into(), port: 443, timeout_ms: 100 }).await;
        assert!(r.is_err());
    }

    #[tokio::test]
    async fn localhost_unreachable_port() {
        // Port 1 on localhost almost certainly closed — assert unreachable, not error
        let r = trace(TraceRequest { target: "127.0.0.1".into(), port: 1, timeout_ms: 200 }).await;
        let resp = r.expect("trace should not error");
        assert_eq!(resp.hops.len(), 1);
        assert!(!resp.hops[0].reachable);
    }

    #[tokio::test]
    async fn defaults_applied() {
        let req: TraceRequest = serde_json::from_str(r#"{"target":"1.1.1.1"}"#).unwrap();
        assert_eq!(req.port, 443);
        assert_eq!(req.timeout_ms, 1000);
    }
}
