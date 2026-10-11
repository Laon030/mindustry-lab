package agentbridge;

import arc.util.serialization.JsonValue;
import arc.util.serialization.JsonWriter;
import mindustry.Vars;
import mindustry.ai.types.CommandAI;
import mindustry.content.Items;
import mindustry.content.Blocks;
import mindustry.content.UnitTypes;
import mindustry.game.Team;
import mindustry.gen.Groups;
import mindustry.gen.Unit;
import mindustry.gen.Building;
import mindustry.world.Build;
import mindustry.world.Tile;
import mindustry.world.blocks.ConstructBlock.ConstructBuild;
import mindustry.world.blocks.units.UnitFactory;
import mindustry.world.blocks.units.UnitFactory.UnitFactoryBuild;
import mindustry.world.blocks.storage.CoreBlock;

/** Omniscient, symmetric observation for the controlled localhost duel demo. Game thread only. */
final class DuelStateCapture {
    private DuelStateCapture() {}

    static String capture() {
        if (!Vars.state.isGame()) return "{\"status\":\"waiting\"}";

        JsonValue out = object(), teams = object();
        put(out, "contract", "DUEL_DEMO_OMNISCIENT_V0");
        put(out, "worldId", DemoObservation.worldId());
        put(out, "tick", (long) Vars.state.tick);
        put(out, "paused", Vars.state.isPaused());
        put(out, "gameOver", Vars.state.gameOver);
        for (Team team : new Team[]{Team.sharded, Team.crux}) {
            JsonValue view = object(), resources = object(), cores = array(), units = array();
            put(resources, "copper", team.items().get(Items.copper));
            put(resources, "lead", team.items().get(Items.lead));
            view.addChild("resources", resources);
            for (CoreBlock.CoreBuild core : team.data().cores) {
                JsonValue entry = object();
                put(entry, "x", core.tileX());
                put(entry, "y", core.tileY());
                put(entry, "health", core.health);
                cores.addChild(entry);
            }
            view.addChild("cores", cores);
            JsonValue economy = object(), site = object();
            CoreBlock.CoreBuild home = team.core();
            int oreCount = 0;
            if (home != null) {
                for (int x = Math.max(0, home.tileX() - 16); x <= Math.min(Vars.world.width() - 1, home.tileX() + 16); x++) {
                    for (int y = Math.max(0, home.tileY() - 16); y <= Math.min(Vars.world.height() - 1, home.tileY() + 16); y++) {
                        Tile tile = Vars.world.tile(x, y);
                        if (tile != null && tile.drop() == Items.copper && tile.block() == Blocks.air) oreCount++;
                    }
                }
                int sx = home.tileX() - 8, sy = home.tileY();
                Tile tile = Vars.world.tile(sx, sy);
                put(site, "x", sx); put(site, "y", sy);
                put(site, "block", Blocks.duo.name);
                put(site, "copperCost", Blocks.duo.requirements[0].amount);
                put(site, "placeable", Build.validPlace(Blocks.duo, team, sx, sy, 0));
                if (tile != null && tile.block() == Blocks.duo && tile.team() == team) {
                    put(site, "status", "complete");
                } else if (tile != null && tile.build instanceof ConstructBuild construction
                        && construction.current == Blocks.duo && tile.team() == team) {
                    put(site, "status", "constructing");
                    put(site, "progress", construction.progress);
                } else {
                    put(site, "status", "empty");
                }
            } else {
                put(site, "status", "no-core");
            }
            put(economy, "nearbyCopperOreTiles", oreCount);
            economy.addChild("duoSite", site);
            view.addChild("economy", economy);
            JsonValue production = object(), factory = object();
            if (home != null) {
                int fx = home.tileX() - 8, fy = home.tileY() + 6;
                put(factory, "x", fx); put(factory, "y", fy);
                put(factory, "block", Blocks.groundFactory.name);
                put(factory, "unit", UnitTypes.dagger.name);
                var recipe = ((UnitFactory) Blocks.groundFactory).plans.get(0);
                JsonValue cost = object();
                for (var stack : recipe.requirements) put(cost, stack.item.name, stack.amount);
                factory.addChild("cost", cost);
                Tile tile = Vars.world.tile(fx, fy);
                if (tile != null && tile.build instanceof UnitFactoryBuild build && build.team == team) {
                    JsonValue stock = object();
                    put(stock, "silicon", build.items.get(Items.silicon));
                    put(stock, "lead", build.items.get(Items.lead));
                    factory.addChild("stock", stock);
                    Tile reserveTile = Vars.world.tile(fx + 4, fy);
                    Tile unloaderTile = Vars.world.tile(fx + 2, fy);
                    boolean supplyRouteReady = reserveTile != null && reserveTile.build != null
                            && reserveTile.block() == Blocks.vault && reserveTile.team() == team
                            && unloaderTile != null && unloaderTile.block() == Blocks.unloader
                            && unloaderTile.team() == team;
                    JsonValue reserve = object();
                    put(reserve, "routeReady", supplyRouteReady);
                    JsonValue reserveStock = object();
                    put(reserveStock, "silicon", supplyRouteReady
                            ? reserveTile.build.items.get(Items.silicon) : 0);
                    put(reserveStock, "lead", supplyRouteReady
                            ? reserveTile.build.items.get(Items.lead) : 0);
                    reserve.addChild("stock", reserveStock);
                    factory.addChild("supply", reserve);
                    put(factory, "status", build.currentPlan == -1 ? "idle" : "active");
                    put(factory, "progress", build.progress);
                    put(factory, "powerStatus", build.power.status);
                } else {
                    put(factory, "status", "absent");
                }
            } else {
                put(factory, "status", "no-core");
            }
            production.addChild("factory", factory);
            view.addChild("production", production);
            JsonValue buildings = array();
            for (Building building : Groups.build) {
                if (building.team != team || building.block == Blocks.coreShard) continue;
                JsonValue entry = object();
                put(entry, "block", building.block.name);
                put(entry, "x", building.tileX()); put(entry, "y", building.tileY());
                buildings.addChild(entry);
            }
            view.addChild("buildings", buildings);
            for (Unit unit : Groups.unit) {
                if (unit.team != team || !unit.isAdded() || unit.dead || unit.health <= 0) continue;
                JsonValue entry = object();
                put(entry, "id", unit.id);
                put(entry, "type", unit.type.name);
                put(entry, "x", unit.x);
                put(entry, "y", unit.y);
                put(entry, "health", unit.health);
                put(entry, "maxHealth", unit.maxHealth);
                put(entry, "commandable", unit.controller() instanceof CommandAI);
                units.addChild(entry);
            }
            view.addChild("units", units);
            teams.addChild(team.name, view);
        }
        out.addChild("teams", teams);
        return out.toJson(JsonWriter.OutputType.json);
    }

    private static JsonValue object() { return new JsonValue(JsonValue.ValueType.object); }
    private static JsonValue array() { return new JsonValue(JsonValue.ValueType.array); }
    private static void put(JsonValue value, String key, String text) { value.addChild(key, new JsonValue(text)); }
    private static void put(JsonValue value, String key, boolean flag) { value.addChild(key, new JsonValue(flag)); }
    private static void put(JsonValue value, String key, long number) { value.addChild(key, new JsonValue(number)); }
    private static void put(JsonValue value, String key, double number) { value.addChild(key, new JsonValue(number)); }
}
