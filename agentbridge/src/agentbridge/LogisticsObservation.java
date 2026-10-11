package agentbridge;

import arc.struct.ObjectIntMap;
import arc.util.serialization.JsonValue;
import arc.util.serialization.JsonWriter;
import mindustry.Vars;
import mindustry.content.Blocks;
import mindustry.content.Items;
import mindustry.game.Team;
import mindustry.gen.Building;
import mindustry.type.Item;
import mindustry.type.ItemStack;
import mindustry.world.Block;
import mindustry.world.Build;
import mindustry.world.Tile;
import mindustry.world.blocks.ConstructBlock.ConstructBuild;
import mindustry.world.blocks.distribution.Conveyor.ConveyorBuild;
import mindustry.world.blocks.production.Drill;
import mindustry.world.blocks.production.Drill.DrillBuild;

/** Bounded observations for the early-game copper logistics proof-of-concept. */
public class LogisticsObservation {
    public static final int scanRadius = 48;

    public static String capture(Team team, boolean includePlanning) {
        JsonValue out = object();
        Building core = team.core();
        if (core == null) return json(out);

        int minX = Math.max(0, core.tileX() - scanRadius);
        int maxX = Math.min(Vars.world.width() - 1, core.tileX() + scanRadius);
        int minY = Math.max(0, core.tileY() - scanRadius);
        int maxY = Math.min(Vars.world.height() - 1, core.tileY() + scanRadius);

        JsonValue bounds = object();
        put(bounds, "minX", minX); put(bounds, "maxX", maxX);
        put(bounds, "minY", minY); put(bounds, "maxY", maxY);
        out.addChild("bounds", bounds);

        JsonValue coreJson = object();
        put(coreJson, "tileX", core.tileX());
        put(coreJson, "tileY", core.tileY());
        put(coreJson, "size", core.block.size);
        put(coreJson, "copper", core.items.get(Items.copper));
        put(coreJson, "receivedCopper", Vars.state.stats.coreItemCount.get(Items.copper));
        coreJson.addChild("footprint", footprint(core.tileX(), core.tileY(), core.block.size));
        out.addChild("core", coreJson);

        JsonValue content = object();
        content.addChild("drill", content(Blocks.mechanicalDrill));
        content.addChild("conveyor", content(Blocks.conveyor));
        out.addChild("content", content);

        JsonValue buildings = array();
        for (int x = minX; x <= maxX; x++) {
            for (int y = minY; y <= maxY; y++) {
                Tile tile = Vars.world.tile(x, y);
                if (tile == null || tile.build == null || tile.build.tile != tile) continue;
                buildings.addChild(building(tile.build));
            }
        }
        out.addChild("buildings", buildings);

        if (includePlanning) {
            JsonValue oreTiles = array(), drillCandidates = array(), conveyorCells = array();
            for (int x = minX; x <= maxX; x++) {
                for (int y = minY; y <= maxY; y++) {
                    Tile tile = Vars.world.tile(x, y);
                    if (tile == null) continue;
                    if (tile.drop() == Items.copper) oreTiles.addChild(point(x, y));

                    int mask = 0;
                    for (int rotation = 0; rotation < 4; rotation++) {
                        if (Build.validPlace(Blocks.conveyor, team, x, y, rotation)) mask |= 1 << rotation;
                    }
                    if (mask != 0) {
                        JsonValue cell = array();
                        cell.addChild(number(x)); cell.addChild(number(y)); cell.addChild(number(mask));
                        conveyorCells.addChild(cell);
                    }

                    if (Build.validPlace(Blocks.mechanicalDrill, team, x, y, 0)) {
                        OreResult ore = dominantOre(x, y, (Drill)Blocks.mechanicalDrill);
                        if (ore.item == Items.copper) {
                            JsonValue candidate = object();
                            put(candidate, "tileX", x); put(candidate, "tileY", y);
                            put(candidate, "oreItem", ore.item.name); put(candidate, "oreTiles", ore.count);
                            candidate.addChild("footprint", footprint(x, y, Blocks.mechanicalDrill.size));
                            drillCandidates.addChild(candidate);
                        }
                    }
                }
            }
            out.addChild("oreTiles", oreTiles);
            out.addChild("drillCandidates", drillCandidates);
            out.addChild("conveyorCells", conveyorCells);
        }
        return json(out);
    }

    private static JsonValue content(Block block) {
        JsonValue out = object(), requirements = object();
        put(out, "name", block.name); put(out, "size", block.size);
        for (ItemStack stack : block.requirements) {
            put(requirements, stack.item.name,
                    Math.round(stack.amount * Vars.state.rules.buildCostMultiplier));
        }
        out.addChild("requirements", requirements);
        if (block instanceof Drill drill) {
            put(out, "tier", drill.tier); put(out, "drillTime", drill.drillTime);
            put(out, "copperHardness", Items.copper.hardness);
        }
        return out;
    }

    private static JsonValue building(Building build) {
        JsonValue out = object();
        put(out, "tileX", build.tileX()); put(out, "tileY", build.tileY());
        put(out, "block", build.block.name); put(out, "team", build.team.name);
        put(out, "size", build.block.size); put(out, "rotation", build.rotation);
        put(out, "copper", build.items == null ? 0 : build.items.get(Items.copper));
        if (build instanceof ConstructBuild construction) {
            put(out, "constructing", construction.current.name);
            put(out, "progress", construction.progress);
        }
        if (build instanceof DrillBuild drill) {
            put(out, "dominantItem", drill.dominantItem == null ? "none" : drill.dominantItem.name);
            put(out, "dominantTiles", drill.dominantItems);
            put(out, "progress", drill.progress());
            put(out, "warmup", drill.warmup);
            put(out, "lastDrillSpeed", drill.lastDrillSpeed);
        }
        if (build instanceof ConveyorBuild conveyor) put(out, "itemCount", conveyor.len);
        return out;
    }

    private static OreResult dominantOre(int x, int y, Drill drill) {
        ObjectIntMap<Item> counts = new ObjectIntMap<>();
        int offset = -(drill.size - 1) / 2;
        for (int dx = 0; dx < drill.size; dx++) {
            for (int dy = 0; dy < drill.size; dy++) {
                Tile tile = Vars.world.tile(x + offset + dx, y + offset + dy);
                if (drill.canMine(tile)) counts.increment(tile.drop(), 0, 1);
            }
        }
        Item best = null;
        int bestCount = 0;
        for (Item item : counts.keys()) {
            int count = counts.get(item, 0);
            if (best == null || compareOre(best, bestCount, item, count) < 0) {
                best = item; bestCount = count;
            }
        }
        return new OreResult(best, bestCount);
    }

    // Same ordering used by Drill.countOre(): normal items, then count, then item ID.
    private static int compareOre(Item first, int firstCount, Item second, int secondCount) {
        int priority = Boolean.compare(!first.lowPriority, !second.lowPriority);
        if (priority != 0) return priority;
        int count = Integer.compare(firstCount, secondCount);
        return count != 0 ? count : Integer.compare(first.id, second.id);
    }

    private static JsonValue footprint(int x, int y, int size) {
        JsonValue out = array();
        int offset = -(size - 1) / 2;
        for (int dx = 0; dx < size; dx++) {
            for (int dy = 0; dy < size; dy++) out.addChild(point(x + offset + dx, y + offset + dy));
        }
        return out;
    }

    private static JsonValue point(int x, int y) {
        JsonValue out = array(); out.addChild(number(x)); out.addChild(number(y)); return out;
    }
    private static JsonValue number(long value) { return new JsonValue(value); }
    private static JsonValue object() { return new JsonValue(JsonValue.ValueType.object); }
    private static JsonValue array() { return new JsonValue(JsonValue.ValueType.array); }
    private static void put(JsonValue object, String key, String value) { object.addChild(key, new JsonValue(value)); }
    private static void put(JsonValue object, String key, long value) { object.addChild(key, number(value)); }
    private static void put(JsonValue object, String key, double value) { object.addChild(key, new JsonValue(value)); }
    private static String json(JsonValue value) { return value.toJson(JsonWriter.OutputType.json); }

    private record OreResult(Item item, int count) {}
}
