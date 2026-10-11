package agentbridge;

import arc.Core;
import arc.util.serialization.JsonReader;
import arc.util.serialization.JsonValue;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import mindustry.Vars;
import mindustry.core.GameState.State;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/** Local demo timing control only; keeps model calls on one frozen game snapshot. */
final class DuelControlHandler implements HttpHandler {
    @Override
    public void handle(HttpExchange exchange) throws IOException {
        if (!"/duel/control".equals(exchange.getRequestURI().getPath())) {
            send(exchange, 404, "{\"error\":\"Unknown duel path\"}");
            return;
        }
        if (!"POST".equals(exchange.getRequestMethod())) {
            send(exchange, 405, "{\"error\":\"Method not allowed\"}");
            return;
        }
        byte[] bytes = exchange.getRequestBody().readNBytes(513);
        if (bytes.length > 512) {
            send(exchange, 413, "{\"error\":\"Request too large\"}");
            return;
        }
        AtomicReference<Result> result = new AtomicReference<>();
        CountDownLatch latch = new CountDownLatch(1);
        Core.app.post(() -> {
            try {
                if (!Vars.state.isGame()) {
                    result.set(new Result(400, "{\"error\":\"No game running\"}"));
                } else {
                    JsonValue request = new JsonReader().parse(new String(bytes, StandardCharsets.UTF_8));
                    JsonValue paused = request.get("paused");
                    if (!request.isObject() || request.size != 2
                            || !DemoObservation.worldId().equals(request.getString("worldId", ""))
                            || paused == null || !paused.isBoolean()) {
                        result.set(new Result(400, "{\"error\":\"Invalid world or pause request\"}"));
                    } else {
                        Vars.state.set(paused.asBoolean() ? State.paused : State.playing);
                        result.set(new Result(200, "{\"worldId\":\"" + DemoObservation.worldId()
                                + "\",\"paused\":" + Vars.state.isPaused()
                                + ",\"tick\":" + (long) Vars.state.tick + "}"));
                    }
                }
            } catch (Exception failure) {
                result.set(new Result(400, "{\"error\":\"Invalid pause request\"}"));
            } finally {
                latch.countDown();
            }
        });
        boolean complete;
        try {
            complete = latch.await(5, TimeUnit.SECONDS);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            complete = false;
        }
        Result reply = complete ? result.get()
                : new Result(503, "{\"error\":\"Game thread timed out\"}");
        send(exchange, reply.status, reply.body);
    }

    private static void send(HttpExchange exchange, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json");
        exchange.sendResponseHeaders(status, bytes.length);
        try (OutputStream output = exchange.getResponseBody()) {
            output.write(bytes);
        }
        exchange.close();
    }

    private record Result(int status, String body) {}
}
