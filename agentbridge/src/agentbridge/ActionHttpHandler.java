package agentbridge;

import arc.Core;
import arc.util.Log;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpExchange;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

public class ActionHttpHandler implements HttpHandler {

    @Override
    public void handle(HttpExchange exchange) throws IOException {
        if (!"POST".equals(exchange.getRequestMethod())) {
            sendResponse(exchange, 405, "{\"error\":\"Method not allowed\"}");
            return;
        }

        String requestBody;
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(exchange.getRequestBody(), StandardCharsets.UTF_8))) {
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                sb.append(line);
            }
            requestBody = sb.toString();
        }

        AtomicReference<ActionHandler.Result> resultRef = new AtomicReference<>();
        CountDownLatch latch = new CountDownLatch(1);

        Core.app.post(() -> {
            try {
                ActionRequest request = parseRequest(requestBody);
                if (request == null) {
                    resultRef.set(ActionHandler.Result.error(null, "Invalid request format"));
                } else if ("move".equals(request.action)) {
                    if (request.x == null || request.y == null) {
                        resultRef.set(ActionHandler.Result.error("move", "Missing x or y coordinates"));
                    } else {
                        ActionHandler.Result result = ActionHandler.handleMoveAction(request.unitId, request.x, request.y);
                        resultRef.set(result);
                    }
                } else if ("mine".equals(request.action)) {
                    if (request.resource == null) {
                        resultRef.set(ActionHandler.Result.error("mine", "Missing resource parameter"));
                    } else {
                        ActionHandler.Result result = ActionHandler.handleMineAction(request.unitId, request.resource);
                        resultRef.set(result);
                    }
                } else if ("build".equals(request.action)) {
                    if (request.block == null) {
                        resultRef.set(ActionHandler.Result.error("build", "Missing block parameter"));
                    } else if (request.tileX == null || request.tileY == null) {
                        resultRef.set(ActionHandler.Result.error("build", "Missing tileX or tileY"));
                    } else if (request.rotation == null) {
                        resultRef.set(ActionHandler.Result.error("build", "Missing rotation"));
                    } else {
                        ActionHandler.Result result = ActionHandler.handleBuildAction(
                            request.unitId, request.block, request.tileX, request.tileY, request.rotation);
                        resultRef.set(result);
                    }
                } else {
                    resultRef.set(ActionHandler.Result.error(null, "Unknown action: " + request.action));
                }
            } catch (Exception e) {
                Log.err("Action handler error", e);
                resultRef.set(ActionHandler.Result.error(null, "Internal error: " + e.getMessage()));
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

        ActionHandler.Result result;
        if (!completed) {
            result = ActionHandler.Result.error(null, "Action execution timed out");
        } else {
            result = resultRef.get();
        }

        int statusCode = result != null && result.success ? 200 : 400;
        sendResponse(exchange, statusCode, result != null ? result.toJson() : "{\"error\":\"Unknown error\"}");
    }

    private ActionRequest parseRequest(String json) {
        if (json == null || json.trim().isEmpty()) {
            return null;
        }

        try {
            ActionRequest request = new ActionRequest();
            
            String action = extractStringValue(json, "action");
            if (action == null) return null;
            request.action = action;

            Integer unitId = extractIntValue(json, "unitId");
            if (unitId == null) return null;
            request.unitId = unitId;

            Float x = extractFloatValue(json, "x");
            request.x = x;

            Float y = extractFloatValue(json, "y");
            request.y = y;

            String resource = extractStringValue(json, "resource");
            request.resource = resource;

            String block = extractStringValue(json, "block");
            request.block = block;

            Integer tileX = extractIntValue(json, "tileX");
            request.tileX = tileX;

            Integer tileY = extractIntValue(json, "tileY");
            request.tileY = tileY;

            Integer rotation = extractIntValue(json, "rotation");
            request.rotation = rotation;

            return request;
        } catch (Exception e) {
            return null;
        }
    }

    private String extractStringValue(String json, String key) {
        String searchKey = "\"" + key + "\"";
        int keyIndex = json.indexOf(searchKey);
        if (keyIndex == -1) return null;

        int colonIndex = json.indexOf(':', keyIndex + searchKey.length());
        if (colonIndex == -1) return null;

        int quoteStart = json.indexOf('"', colonIndex + 1);
        if (quoteStart == -1) return null;

        int quoteEnd = json.indexOf('"', quoteStart + 1);
        if (quoteEnd == -1) return null;

        return json.substring(quoteStart + 1, quoteEnd);
    }

    private Integer extractIntValue(String json, String key) {
        String searchKey = "\"" + key + "\"";
        int keyIndex = json.indexOf(searchKey);
        if (keyIndex == -1) return null;

        int colonIndex = json.indexOf(':', keyIndex + searchKey.length());
        if (colonIndex == -1) return null;

        int startIndex = colonIndex + 1;
        while (startIndex < json.length() && Character.isWhitespace(json.charAt(startIndex))) {
            startIndex++;
        }

        int endIndex = startIndex;
        while (endIndex < json.length() && (Character.isDigit(json.charAt(endIndex)) || json.charAt(endIndex) == '-')) {
            endIndex++;
        }

        if (endIndex == startIndex) return null;

        try {
            return Integer.parseInt(json.substring(startIndex, endIndex));
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private Float extractFloatValue(String json, String key) {
        String searchKey = "\"" + key + "\"";
        int keyIndex = json.indexOf(searchKey);
        if (keyIndex == -1) return null;

        int colonIndex = json.indexOf(':', keyIndex + searchKey.length());
        if (colonIndex == -1) return null;

        int startIndex = colonIndex + 1;
        while (startIndex < json.length() && Character.isWhitespace(json.charAt(startIndex))) {
            startIndex++;
        }

        int endIndex = startIndex;
        while (endIndex < json.length() && (Character.isDigit(json.charAt(endIndex)) || json.charAt(endIndex) == '-' || json.charAt(endIndex) == '.')) {
            endIndex++;
        }

        if (endIndex == startIndex) return null;

        try {
            return Float.parseFloat(json.substring(startIndex, endIndex));
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private void sendResponse(HttpExchange exchange, int statusCode, String body) {
        byte[] bodyBytes = body.getBytes(StandardCharsets.UTF_8);
        try {
            exchange.getResponseHeaders().set("Content-Type", "application/json");
            exchange.sendResponseHeaders(statusCode, bodyBytes.length);
            try (OutputStream os = exchange.getResponseBody()) {
                os.write(bodyBytes);
            }
        } catch (IOException e) {
            Log.err("Failed to send response", e);
        } finally {
            exchange.close();
        }
    }

    private static class ActionRequest {
        String action;
        int unitId;
        Float x;
        Float y;
        String resource;
        String block;
        Integer tileX;
        Integer tileY;
        Integer rotation;
    }
}
