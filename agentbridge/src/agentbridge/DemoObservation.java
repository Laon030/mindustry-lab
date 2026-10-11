package agentbridge;

import arc.util.serialization.JsonValue;
import arc.util.serialization.JsonWriter;
import mindustry.Vars;
import mindustry.ai.ItemUnitStance;
import mindustry.ai.UnitCommand;
import mindustry.ai.types.CommandAI;
import mindustry.content.Blocks;
import mindustry.content.Items;
import mindustry.entities.units.BuildPlan;
import mindustry.game.Team;
import mindustry.gen.Groups;
import mindustry.gen.Unit;
import mindustry.type.Item;
import mindustry.world.Build;
import mindustry.world.Tile;
import mindustry.world.blocks.ConstructBlock.ConstructBuild;

import java.util.UUID;

/** Bounded, read-only demo telemetry. All methods run on the game thread. */
public class DemoObservation {
    private static String worldId = UUID.randomUUID().toString();

    public static void resetWorld() {
        worldId = UUID.randomUUID().toString();
    }

    static String worldId() {
        return worldId;
    }

    public static String capture(Team team, Integer centerX, Integer centerY, int radius) {
        JsonValue out = object();
        put(out, "worldId", worldId);
        put(out, "commandReady", Groups.player.contains(p -> p.team() == team));
        put(out, "infiniteResources", Vars.state.rules.infiniteResources || team.rules().infiniteResources);
        put(out, "instantBuild", Vars.state.rules.instantBuild);
        put(out, "conveyorCopperCost", Math.round(Blocks.conveyor.requirements[0].amount * Vars.state.rules.buildCostMultiplier));
        JsonValue ores = object();
        for (Item item : new Item[]{Items.copper, Items.lead}) put(ores, item.name, hasOre(item));
        out.addChild("ores", ores);
        JsonValue area = object(), tiles = array();
        if (team.core() != null) {
            int x = centerX == null ? Math.max(0, team.core().tileX() - 38) : centerX;
            int y = centerY == null ? Math.min(Vars.world.height() - 1, team.core().tileY() + 7) : centerY;
            if (Vars.world.tile(x, y) == null) throw new IllegalArgumentException("Demo area center outside map");
            put(area, "tileX", x);
            put(area, "tileY", y);
            put(area, "radius", radius);
            for (int tx = x - radius; tx <= x + radius; tx++) {
                for (int ty = y - radius; ty <= y + radius; ty++) {
                    Tile tile = Vars.world.tile(tx, ty);
                    if (tile == null) continue;
                    JsonValue entry = object(), rotations = array();
                    put(entry, "id", tx + ":" + ty);
                    put(entry, "tileX", tx);
                    put(entry, "tileY", ty);
                    put(entry, "block", tile.block().name);
                    put(entry, "team", tile.team().name);
                    put(entry, "rotation", tile.build == null ? -1 : tile.build.rotation);
                    if (tile.build instanceof ConstructBuild construction) {
                        put(entry, "constructing", construction.current.name);
                        put(entry, "progress", construction.progress);
                    }
                    // Empty tiles only: demo candidates never replace an existing building.
                    if (tile.block() == Blocks.air) {
                        for (int rotation = 0; rotation < 4; rotation++) {
                            if (Build.validPlace(Blocks.conveyor, team, tx, ty, rotation)) {
                                rotations.addChild(new JsonValue((long) rotation));
                            }
                        }
                    }
                    entry.addChild("buildRotations", rotations);
                    tiles.addChild(entry);
                }
            }
        }
        area.addChild("tiles", tiles);
        out.addChild("area", area);
        return json(out);
    }

    public static String activity(Unit unit) {
        JsonValue out = object(), plans = array(), resources = array();
        CommandAI ai = unit.controller() instanceof CommandAI command ? command : null;
        put(out, "commandable", ai != null);
        put(out, "command", ai == null ? "unavailable" : ai.currentCommand().name);
        put(out, "canBuild", ai != null && unit.canBuild()
                && unit.type.allowCommand(unit, UnitCommand.rebuildCommand));
        put(out, "buildRange", unit.type.buildRange);
        String mineResource = null;
        for (Item item : new Item[]{Items.copper, Items.lead}) {
            if (ai != null && unit.canMine(item) && hasOre(item)) resources.addChild(new JsonValue(item.name));
            if (ai != null && ai.currentCommand() == UnitCommand.mineCommand
                    && ai.hasStance(ItemUnitStance.getByItem(item))) {
                mineResource = mineResource == null ? item.name : "multiple";
            }
        }
        if (mineResource != null) put(out, "mineResource", mineResource);
        out.addChild("mineResources", resources);
        put(out, "mining", unit.mineTile != null);
        put(out, "item", unit.stack.item == null ? "none" : unit.stack.item.name);
        put(out, "itemAmount", unit.stack.amount);
        put(out, "planCount", unit.plans.size);
        int count = 0;
        for (BuildPlan plan : unit.plans) {
            if (count++ == 8) break;
            JsonValue entry = object();
            put(entry, "tileX", plan.x);
            put(entry, "tileY", plan.y);
            put(entry, "block", plan.block == null ? "none" : plan.block.name);
            put(entry, "rotation", plan.rotation);
            put(entry, "breaking", plan.breaking);
            put(entry, "progress", plan.progress);
            plans.addChild(entry);
        }
        out.addChild("plans", plans);
        return json(out);
    }

    private static boolean hasOre(Item item) {
        return Vars.indexer.hasOre(item) || Vars.indexer.hasWallOre(item);
    }

    private static JsonValue object() { return new JsonValue(JsonValue.ValueType.object); }
    private static JsonValue array() { return new JsonValue(JsonValue.ValueType.array); }
    private static void put(JsonValue object, String key, String value) { object.addChild(key, new JsonValue(value)); }
    private static void put(JsonValue object, String key, boolean value) { object.addChild(key, new JsonValue(value)); }
    private static void put(JsonValue object, String key, long value) { object.addChild(key, new JsonValue(value)); }
    private static void put(JsonValue object, String key, double value) { object.addChild(key, new JsonValue(value)); }
    private static String json(JsonValue value) { return value.toJson(JsonWriter.OutputType.json); }
}
