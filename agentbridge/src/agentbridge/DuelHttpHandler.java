package agentbridge;

import arc.Core;
import arc.math.geom.Vec2;
import arc.util.Log;
import arc.util.serialization.JsonReader;
import arc.util.serialization.JsonValue;
import arc.util.serialization.JsonWriter;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import mindustry.Vars;
import mindustry.ai.ItemUnitStance;
import mindustry.ai.UnitCommand;
import mindustry.ai.UnitStance;
import mindustry.ai.types.CommandAI;
import mindustry.content.Blocks;
import mindustry.content.Items;
import mindustry.content.UnitTypes;
import mindustry.entities.units.BuildPlan;
import mindustry.game.Team;
import mindustry.gen.Groups;
import mindustry.gen.Player;
import mindustry.gen.Unit;
import mindustry.input.InputHandler;
import mindustry.world.Build;
import mindustry.world.Tile;
import mindustry.world.blocks.units.UnitFactory;
import mindustry.world.blocks.units.UnitFactory.UnitFactoryBuild;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.HashSet;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/** Narrow, localhost-only transport for the controlled duel demo. All game access runs on Core.app. */
final class DuelHttpHandler implements HttpHandler {
    private final boolean action;

    DuelHttpHandler(boolean action) {
        this.action = action;
    }

    @Override
    public void handle(HttpExchange exchange) throws IOException {
        String path = action ? "/duel/action" : "/duel/state";
        if (!path.equals(exchange.getRequestURI().getPath())) {
            send(exchange, 404, error("Unknown duel path"));
            return;
        }
        if (!(action ? "POST" : "GET").equals(exchange.getRequestMethod())) {
            send(exchange, 405, error("Method not allowed"));
            return;
        }
        byte[] request = action ? exchange.getRequestBody().readNBytes(8193) : new byte[0];
        if (request.length > 8192) {
            send(exchange, 413, error("Request too large"));
            return;
        }

        AtomicReference<Response> result = new AtomicReference<>();
        CountDownLatch latch = new CountDownLatch(1);
        Core.app.post(() -> {
            try {
                result.set(action ? execute(new String(request, StandardCharsets.UTF_8))
                        : new Response(200, DuelStateCapture.capture()));
            } catch (Exception failure) {
                Log.err("Duel endpoint failed", failure);
                result.set(new Response(400, error("Invalid duel request: " + failure.getMessage())));
            } finally {
                latch.countDown();
            }
        });

        boolean completed;
        try {
            completed = latch.await(5, TimeUnit.SECONDS);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            completed = false;
        }
        Response response = completed ? result.get() : new Response(503, error("Game thread timed out"));
        send(exchange, response.status, response.body);
    }

    private static Response execute(String body) {
        if (!Vars.state.isGame()) return new Response(400, error("No game running"));
        JsonValue request = new JsonReader().parse(body);
        if (!request.isObject()) return new Response(400, error("Expected JSON object"));
        String teamName = request.getString("team", "");
        Team team = "sharded".equals(teamName) ? Team.sharded
                : "crux".equals(teamName) ? Team.crux : null;
        if (team == null) return new Response(400, error("Unknown team"));
        String command = request.getString("action", "");
        if (!"move".equals(command) && !"attack".equals(command)
                && !"mine".equals(command) && !"build".equals(command)
                && !"produce".equals(command)) {
            return new Response(400, error("Unsupported duel action"));
        }
        if ("produce".equals(command)) return executeProduction(request, team);
        JsonValue list = request.get("unitIds");
        if (list == null || !list.isArray() || list.size < 1 || list.size > 40) {
            return new Response(400, error("unitIds must contain 1-40 IDs"));
        }
        int[] ids = new int[list.size];
        HashSet<Integer> unique = new HashSet<>();
        int index = 0;
        for (JsonValue value = list.child; value != null; value = value.next) {
            int id = value.asInt();
            if (!unique.add(id)) return new Response(400, error("Duplicate unit ID"));
            Unit unit = Groups.unit.getByID(id);
            if (unit == null || !unit.isAdded() || unit.dead || unit.health <= 0
                    || unit.team != team || !(unit.controller() instanceof CommandAI)) {
                return new Response(400, error("Unit unavailable or not owned by team: " + id));
            }
            ids[index++] = id;
        }

        Unit target = null;
        Vec2 position = null;
        if ("attack".equals(command)) {
            target = Groups.unit.getByID(request.getInt("targetUnitId"));
            if (target == null || !target.isAdded() || target.dead || target.health <= 0 || target.team == team) {
                return new Response(400, error("Invalid enemy target"));
            }
            for (int id : ids) {
                if (!Groups.unit.getByID(id).canTarget(target)) {
                    return new Response(400, error("Unit cannot target enemy: " + id));
                }
            }
        } else if ("move".equals(command)) {
            float x = request.getFloat("x"), y = request.getFloat("y");
            if (!Float.isFinite(x) || !Float.isFinite(y) || x < 0 || y < 0
                    || x >= Vars.world.width() * Vars.tilesize || y >= Vars.world.height() * Vars.tilesize) {
                return new Response(400, error("Move destination outside world"));
            }
            position = new Vec2(x, y);
        }

        // Synthetic team-matched player is a command issuer, not a spawned combat unit.
        // Caller identity/authorization remains the Python coordinator's demo contract.
        Player issuer = Player.create();
        issuer.name("duel-" + team.name);
        issuer.team(team);
        if ("mine".equals(command)) {
            if (ids.length != 1 || !"copper".equals(request.getString("resource", ""))) {
                return new Response(400, error("Gate 5 mining requires one unit and copper"));
            }
            Unit miner = Groups.unit.getByID(ids[0]);
            if (!miner.canMine(Items.copper) || !Vars.indexer.hasOre(Items.copper)) {
                return new Response(400, error("Unit cannot mine copper"));
            }
            CommandAI ai = (CommandAI) miner.controller();
            ItemUnitStance stance = ItemUnitStance.getByItem(Items.copper);
            for (ItemUnitStance other : ItemUnitStance.all()) {
                if (other != stance && ai.hasStance(other)) {
                    InputHandler.setUnitStance(issuer, ids, other, false);
                }
            }
            InputHandler.setUnitCommand(issuer, ids, UnitCommand.mineCommand);
            InputHandler.setUnitStance(issuer, ids, stance, true);
        } else if ("build".equals(command)) {
            if (ids.length != 1 || !Blocks.duo.name.equals(request.getString("block", ""))) {
                return new Response(400, error("Gate 5 building requires one unit and duo"));
            }
            Unit builder = Groups.unit.getByID(ids[0]);
            if (team.core() == null || !builder.canBuild()
                    || !builder.type.allowCommand(builder, UnitCommand.rebuildCommand)) {
                return new Response(400, error("Unit cannot build or team has no core"));
            }
            int x = request.getInt("x"), y = request.getInt("y");
            if (x != team.core().tileX() - 8 || y != team.core().tileY()
                    || !Build.validPlace(Blocks.duo, team, x, y, 0)) {
                return new Response(400, error("Invalid team duo candidate"));
            }
            if (team.items().get(Items.copper) < Blocks.duo.requirements[0].amount) {
                return new Response(400, error("Insufficient copper for duo"));
            }
            CommandAI ai = (CommandAI) builder.controller();
            if (ai.currentCommand() != UnitCommand.rebuildCommand) {
                arc.struct.Seq<BuildPlan> queued = new arc.struct.Seq<>();
                for (BuildPlan existing : builder.plans) queued.add(existing);
                InputHandler.setUnitCommand(issuer, ids, UnitCommand.rebuildCommand);
                for (BuildPlan existing : queued) builder.addBuild(existing, true);
            }
            InputHandler.setUnitStance(issuer, ids, UnitStance.holdPosition, false);
            builder.addBuild(new BuildPlan(x, y, 0, Blocks.duo), true);
        } else {
            InputHandler.commandUnits(issuer, ids, null, target, position, false, true);
        }

        JsonValue accepted = object(), acceptedIds = array();
        accepted.addChild("accepted", new JsonValue(true));
        accepted.addChild("team", new JsonValue(team.name));
        accepted.addChild("action", new JsonValue(command));
        for (int id : ids) acceptedIds.addChild(new JsonValue((long) id));
        accepted.addChild("unitIds", acceptedIds);
        return new Response(200, accepted.toJson(JsonWriter.OutputType.json));
    }

    private static Response executeProduction(JsonValue request, Team team) {
        if (team.core() == null || !UnitTypes.dagger.name.equals(request.getString("unit", ""))) {
            return new Response(400, error("Invalid Dagger production request"));
        }
        int x = request.getInt("buildingX"), y = request.getInt("buildingY");
        if (x != team.core().tileX() - 8 || y != team.core().tileY() + 6) {
            return new Response(400, error("Invalid team factory candidate"));
        }
        Tile tile = Vars.world.tile(x, y);
        if (tile == null || !(tile.build instanceof UnitFactoryBuild factory)
                || factory.team != team || factory.block != Blocks.groundFactory
                || factory.currentPlan != -1) {
            return new Response(400, error("Team factory unavailable or already active"));
        }
        var plan = ((UnitFactory) Blocks.groundFactory).plans.get(0);
        if (plan.unit != UnitTypes.dagger) return new Response(400, error("Unexpected factory recipe"));
        Tile reserveTile = Vars.world.tile(x + 4, y);
        Tile unloaderTile = Vars.world.tile(x + 2, y);
        boolean supplyReady = reserveTile != null && reserveTile.build != null
                && reserveTile.block() == Blocks.vault && reserveTile.team() == team
                && unloaderTile != null && unloaderTile.block() == Blocks.unloader
                && unloaderTile.team() == team;
        for (var stack : plan.requirements) {
            int available = factory.items.get(stack.item)
                    + (supplyReady ? reserveTile.build.items.get(stack.item) : 0);
            if (available < stack.amount) {
                return new Response(400, error("Factory lacks " + stack.item.name));
            }
        }
        Player issuer = Player.create();
        issuer.name("duel-" + team.name);
        issuer.team(team);
        InputHandler.tileConfig(issuer, factory, UnitTypes.dagger);
        if (factory.currentPlan != 0) return new Response(400, error("Factory configuration failed"));
        JsonValue accepted = object();
        accepted.addChild("accepted", new JsonValue(true));
        accepted.addChild("team", new JsonValue(team.name));
        accepted.addChild("action", new JsonValue("produce"));
        accepted.addChild("buildingX", new JsonValue((long)x));
        accepted.addChild("buildingY", new JsonValue((long)y));
        accepted.addChild("unit", new JsonValue(UnitTypes.dagger.name));
        return new Response(200, accepted.toJson(JsonWriter.OutputType.json));
    }

    private static JsonValue object() { return new JsonValue(JsonValue.ValueType.object); }
    private static JsonValue array() { return new JsonValue(JsonValue.ValueType.array); }

    private static String error(String message) {
        JsonValue out = object();
        out.addChild("error", new JsonValue(message == null ? "Invalid request" : message));
        return out.toJson(JsonWriter.OutputType.json);
    }

    private static void send(HttpExchange exchange, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, bytes.length);
        try (OutputStream output = exchange.getResponseBody()) {
            output.write(bytes);
        } finally {
            exchange.close();
        }
    }

    private record Response(int status, String body) {}
}
