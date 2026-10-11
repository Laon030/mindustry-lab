package agentbridge;

import arc.Core;
import arc.math.geom.Vec2;
import arc.util.Log;
import mindustry.Vars;
import mindustry.ai.ItemUnitStance;
import mindustry.ai.UnitCommand;
import mindustry.ai.UnitStance;
import mindustry.ai.types.CommandAI;
import mindustry.content.Blocks;
import mindustry.content.Items;
import mindustry.entities.units.BuildPlan;
import mindustry.gen.Groups;
import mindustry.gen.Player;
import mindustry.gen.Unit;
import mindustry.input.InputHandler;
import mindustry.type.Item;
import mindustry.world.Block;
import mindustry.world.Build;

public class ActionHandler {

    public static Result handleMoveAction(int unitId, float x, float y) {
        if (!Vars.state.isGame()) {
            return Result.error("move", "No game is currently running");
        }

        Unit targetUnit = Groups.unit.getByID(unitId);
        if (targetUnit == null) {
            return Result.error("move", "Unit not found: " + unitId);
        }

        Player player = findPlayerForUnit(targetUnit);
        if (player == null) {
            return Result.error("move", "No player found for unit's team");
        }

        if (targetUnit.team != player.team()) {
            return Result.error("move", "Unit does not belong to player's team");
        }

        if (!(targetUnit.controller() instanceof CommandAI)) {
            return Result.error("move", "Unit is not commandable");
        }

        try {
            InputHandler.commandUnits(player, new int[]{unitId}, null, null, new Vec2(x, y), false, true);
            return Result.successMove(unitId, x, y);
        } catch (Exception e) {
            Log.err("Failed to command unit move", e);
            return Result.error("move", "Command execution failed: " + e.getMessage());
        }
    }

    public static Result handleMineAction(int unitId, String resourceName) {
        if (!Vars.state.isGame()) {
            return Result.error("mine", "No game is currently running");
        }

        Unit targetUnit = Groups.unit.getByID(unitId);
        if (targetUnit == null) {
            return Result.error("mine", "Unit not found: " + unitId);
        }

        Player player = findPlayerForUnit(targetUnit);
        if (player == null) {
            return Result.error("mine", "No player found for unit's team");
        }

        if (targetUnit.team != player.team()) {
            return Result.error("mine", "Unit does not belong to player's team");
        }

        if (!targetUnit.canMine()) {
            return Result.error("mine", "Unit cannot mine");
        }

        Item item = getItemByName(resourceName);
        if (item == null) {
            return Result.error("mine", "Unknown resource: " + resourceName);
        }

        if (!targetUnit.canMine(item)) {
            return Result.error("mine", "Unit cannot mine " + resourceName + " (tier too high)");
        }

        if (!Vars.indexer.hasOre(item) && !Vars.indexer.hasWallOre(item)) {
            return Result.error("mine", "No " + resourceName + " ore found on map");
        }

        if (!(targetUnit.controller() instanceof CommandAI ai)) {
            return Result.error("mine", "Unit is not commandable");
        }

        ItemUnitStance stance = ItemUnitStance.getByItem(item);
        if (stance == null) {
            return Result.error("mine", "Cannot create mining stance for " + resourceName);
        }

        try {
            int[] unitIds = new int[]{unitId};
            // Item mining stances are not mutually exclusive in v159.7. Clear an
            // earlier resource selection so a later command means exactly one item.
            for (ItemUnitStance other : ItemUnitStance.all()) {
                if (other != stance && ai.hasStance(other)) {
                    InputHandler.setUnitStance(player, unitIds, other, false);
                }
            }
            InputHandler.setUnitCommand(player, unitIds, UnitCommand.mineCommand);
            InputHandler.setUnitStance(player, unitIds, stance, true);
            return Result.successMine(unitId, resourceName);
        } catch (Exception e) {
            Log.err("Failed to command unit mine", e);
            return Result.error("mine", "Command execution failed: " + e.getMessage());
        }
    }

    public static Result handleBuildAction(int unitId, String blockName, int tileX, int tileY, int rotation) {
        if (!Vars.state.isGame()) {
            return Result.error("build", "No game is currently running");
        }

        Unit targetUnit = Groups.unit.getByID(unitId);
        if (targetUnit == null) {
            return Result.error("build", "Unit not found: " + unitId);
        }

        Player player = findPlayerForUnit(targetUnit);
        if (player == null) {
            return Result.error("build", "No player found for unit's team");
        }

        if (targetUnit.team != player.team()) {
            return Result.error("build", "Unit does not belong to player's team");
        }

        if (!targetUnit.canBuild()) {
            return Result.error("build", "Unit cannot build (buildSpeed <= 0)");
        }

        Block block = getBlockByName(blockName);
        if (block == null) {
            return Result.error("build", "Unknown block: " + blockName);
        }

        if (!block.canBeBuilt()) {
            return Result.error("build", "Block cannot be built: " + blockName);
        }

        if (!block.isPlaceable()) {
            return Result.error("build", "Block is not placeable: " + blockName);
        }

        if (rotation < 0 || rotation > 3) {
            return Result.error("build", "Rotation must be 0-3, got: " + rotation);
        }

        if (Vars.world.tile(tileX, tileY) == null) {
            return Result.error("build", "Tile does not exist at (" + tileX + ", " + tileY + ")");
        }

        if (!Build.validPlace(block, targetUnit.team, tileX, tileY, rotation)) {
            return Result.error("build", "Invalid placement location for " + blockName + " at (" + tileX + ", " + tileY + ")");
        }

        try {
            BuildPlan plan = new BuildPlan(tileX, tileY, rotation, block);
            if (!(targetUnit.controller() instanceof CommandAI ai)
                    || !targetUnit.type.allowCommand(targetUnit, UnitCommand.rebuildCommand)) {
                return Result.error("build", "Unit does not support autonomous building");
            }
            // BuildPlan does not change the movement controller. A previous move/mine
            // command would otherwise leave an accepted, out-of-range plan stalled.
            if (ai.currentCommand() != UnitCommand.rebuildCommand) {
                arc.struct.Seq<BuildPlan> queued = new arc.struct.Seq<>();
                for (BuildPlan existing : targetUnit.plans) queued.add(existing);
                InputHandler.setUnitCommand(player, new int[]{unitId}, UnitCommand.rebuildCommand);
                for (BuildPlan existing : queued) targetUnit.addBuild(existing, true);
            }
            InputHandler.setUnitStance(player, new int[]{unitId}, UnitStance.holdPosition, false);
            targetUnit.addBuild(plan, true);
            return Result.successBuild(unitId, blockName, tileX, tileY, rotation);
        } catch (Exception e) {
            Log.err("Failed to assign build plan", e);
            return Result.error("build", "Command execution failed: " + e.getMessage());
        }
    }

    private static Item getItemByName(String name) {
        if (name == null) return null;
        switch (name.toLowerCase()) {
            case "copper": return Items.copper;
            case "lead": return Items.lead;
            case "titanium": return Items.titanium;
            case "thorium": return Items.thorium;
            default: return null;
        }
    }

    private static Block getBlockByName(String name) {
        if (name == null) return null;
        return Vars.content.getByName(mindustry.ctype.ContentType.block, name.toLowerCase());
    }

    private static Player findPlayerForUnit(Unit unit) {
        for (Player player : Groups.player) {
            if (player.team() == unit.team) {
                return player;
            }
        }
        return null;
    }

    public static class Result {
        public final boolean success;
        public final String error;
        public final String action;
        public final Integer unitId;
        public final Float x;
        public final Float y;
        public final String resource;
        public final String block;
        public final Integer tileX;
        public final Integer tileY;
        public final Integer rotation;

        private Result(boolean success, String error, String action, Integer unitId, Float x, Float y, 
                       String resource, String block, Integer tileX, Integer tileY, Integer rotation) {
            this.success = success;
            this.error = error;
            this.action = action;
            this.unitId = unitId;
            this.x = x;
            this.y = y;
            this.resource = resource;
            this.block = block;
            this.tileX = tileX;
            this.tileY = tileY;
            this.rotation = rotation;
        }

        public static Result successMove(int unitId, float x, float y) {
            return new Result(true, null, "move", unitId, x, y, null, null, null, null, null);
        }

        public static Result successMine(int unitId, String resource) {
            return new Result(true, null, "mine", unitId, null, null, resource, null, null, null, null);
        }

        public static Result successBuild(int unitId, String block, int tileX, int tileY, int rotation) {
            return new Result(true, null, "build", unitId, null, null, null, block, tileX, tileY, rotation);
        }

        public static Result error(String action, String message) {
            return new Result(false, message, action, null, null, null, null, null, null, null, null);
        }

        public String toJson() {
            StringBuilder json = new StringBuilder();
            json.append("{");
            json.append("\"success\":").append(success);
            
            if (error != null) {
                json.append(",\"error\":\"").append(escapeJson(error)).append("\"");
            }
            
            if (action != null) {
                json.append(",\"action\":\"").append(action).append("\"");
            }
            
            if (unitId != null) {
                json.append(",\"unitId\":").append(unitId);
            }
            
            if (x != null) {
                json.append(",\"x\":").append(x);
            }
            
            if (y != null) {
                json.append(",\"y\":").append(y);
            }
            
            if (resource != null) {
                json.append(",\"resource\":\"").append(resource).append("\"");
            }
            
            if (block != null) {
                json.append(",\"block\":\"").append(block).append("\"");
            }
            
            if (tileX != null) {
                json.append(",\"tileX\":").append(tileX);
            }
            
            if (tileY != null) {
                json.append(",\"tileY\":").append(tileY);
            }
            
            if (rotation != null) {
                json.append(",\"rotation\":").append(rotation);
            }
            
            json.append("}");
            return json.toString();
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
