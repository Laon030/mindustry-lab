package agentbridge;

import arc.Core;
import arc.util.Log;
import com.sun.net.httpserver.HttpServer;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpExchange;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

public class StateHttpServer {
    private final HttpServer server;
    private final int port;

    public StateHttpServer(int port) {
        this.port = port;
        try {
            server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
            server.createContext("/state", new StateHandler());
            server.createContext("/action", new ActionHttpHandler());
            server.createContext("/duel/state", new DuelHttpHandler(false));
            server.createContext("/duel/action", new DuelHttpHandler(true));
            server.createContext("/duel/control", new DuelControlHandler());
            server.setExecutor(null);
        } catch (IOException e) {
            throw new RuntimeException("Failed to create HTTP server", e);
        }
    }

    public void start() {
        server.start();
        Log.info("AgentBridge HTTP server created on port @", port);
    }

    public void stop() {
        server.stop(0);
        Log.info("AgentBridge HTTP server stopped");
    }

    private static class StateHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if (!"GET".equals(exchange.getRequestMethod())) {
                exchange.sendResponseHeaders(405, -1);
                exchange.close();
                return;
            }

            AtomicReference<String> jsonResponse = new AtomicReference<>();
            CountDownLatch latch = new CountDownLatch(1);
            java.util.Map<String, String> parameters = new java.util.HashMap<>();
            try {
                String query = exchange.getRequestURI().getQuery();
                if (query != null && !query.isEmpty()) {
                    for (String pair : query.split("&")) {
                        String[] parts = pair.split("=", -1);
                        if (parts.length != 2 || !java.util.Set.of("tileX", "tileY", "radius", "view").contains(parts[0])
                                || parameters.putIfAbsent(parts[0], parts[1]) != null) {
                            throw new IllegalArgumentException();
                        }
                    }
                }
                String view = parameters.get("view");
                if (view != null && !java.util.Set.of("logistics-plan", "logistics-status").contains(view)) {
                    throw new IllegalArgumentException();
                }
                if (view != null && (parameters.containsKey("tileX") || parameters.containsKey("tileY")
                        || parameters.containsKey("radius"))) throw new IllegalArgumentException();
                if (view == null) {
                    boolean oneCoordinate = parameters.containsKey("tileX") != parameters.containsKey("tileY");
                    int radius = Integer.parseInt(parameters.getOrDefault("radius", "2"));
                    int x = Integer.parseInt(parameters.getOrDefault("tileX", "0"));
                    int y = Integer.parseInt(parameters.getOrDefault("tileY", "0"));
                    if (oneCoordinate || radius < 1 || radius > 6 || x < 0 || y < 0) throw new IllegalArgumentException();
                }
            } catch (IllegalArgumentException invalid) {
                byte[] body = "{\"error\":\"Use view=logistics-plan|logistics-status alone, or optional integer tileX/tileY together and radius 1-6\"}".getBytes(StandardCharsets.UTF_8);
                exchange.getResponseHeaders().set("Content-Type", "application/json");
                exchange.sendResponseHeaders(400, body.length);
                try (OutputStream output = exchange.getResponseBody()) { output.write(body); }
                exchange.close();
                return;
            }

            Core.app.post(() -> {
                try {
                    String view = parameters.get("view");
                    Integer x = parameters.containsKey("tileX") ? Integer.parseInt(parameters.get("tileX")) : null;
                    Integer y = parameters.containsKey("tileY") ? Integer.parseInt(parameters.get("tileY")) : null;
                    int radius = Integer.parseInt(parameters.getOrDefault("radius", "2"));
                    String state = StateCapture.captureState(x, y, radius, view);
                    jsonResponse.set(state);
                } catch (Exception e) {
                    jsonResponse.set("{\"error\":\"" + escapeJson(e.getMessage()) + "\"}");
                }
                latch.countDown();
            });

            boolean completed;
            try {
                completed = latch.await(5, TimeUnit.SECONDS);
            } catch (InterruptedException e) {
                completed = false;
                Thread.currentThread().interrupt();
            }

            String response;
            if (!completed) {
                response = "{\"error\":\"State capture timed out\"}";
            } else {
                response = jsonResponse.get();
            }

            byte[] responseBytes = response.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(200, responseBytes.length);
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(responseBytes);
            }
            exchange.close();
        }

        private static String escapeJson(String s) {
            if (s == null) return "";
            return s.replace("\\", "\\\\")
                    .replace("\"", "\\\"")
                    .replace("\n", "\\n")
                    .replace("\r", "\\r")
                    .replace("\t", "\\t");
        }
    }
}
