package agentbridge;

import arc.struct.Seq;
import mindustry.Vars;
import mindustry.content.Items;
import mindustry.game.Team;
import mindustry.gen.Unit;
import mindustry.world.blocks.storage.CoreBlock;

public class StateCapture {

    public static String captureState() {
        return captureState(null, null, 2, null);
    }

    public static String captureState(Integer centerX, Integer centerY, int radius) {
        return captureState(centerX, centerY, radius, null);
    }

    public static String captureState(Integer centerX, Integer centerY, int radius, String view) {
        // Check if a game is currently active
        if (!Vars.state.isGame()) {
            return "{\"status\":\"waiting\",\"message\":\"No game is currently running\"}";
        }
        
        StringBuilder json = new StringBuilder();
        json.append("{");
        
        // Wave number
        json.append("\"wave\":").append(Vars.state.wave).append(",");
        
        // Tick
        json.append("\"tick\":").append((long) Vars.state.tick).append(",");
        
        // Team
        Team team = Vars.state.rules.defaultTeam;
        json.append("\"team\":\"").append(team.name).append("\",");
        
        // Resources from team inventory
        json.append("\"resources\":{");
        json.append("\"copper\":").append(team.items().get(Items.copper)).append(",");
        json.append("\"lead\":").append(team.items().get(Items.lead));
        json.append("},");
        
        // Cores
        json.append("\"cores\":[");
        Seq<CoreBlock.CoreBuild> cores = team.data().cores;
        if (cores != null && cores.size > 0) {
            for (int i = 0; i < cores.size; i++) {
                CoreBlock.CoreBuild core = cores.get(i);
                if (i > 0) json.append(",");
                json.append("{");
                json.append("\"x\":").append(core.tileX()).append(",");
                json.append("\"y\":").append(core.tileY()).append(",");
                json.append("\"health\":").append(core.health).append(",");
                json.append("\"maxHealth\":").append(core.block.health);
                json.append("}");
            }
        }
        json.append("],");
        
        // Units
        json.append("\"units\":[");
        Seq<Unit> units = team.data().units;
        if (units != null && units.size > 0) {
            for (int i = 0; i < units.size; i++) {
                Unit unit = units.get(i);
                if (i > 0) json.append(",");
                json.append("{");
                json.append("\"id\":").append(unit.id).append(",");
                json.append("\"type\":\"").append(unit.type.name).append("\",");
                json.append("\"x\":").append(unit.x).append(",");
                json.append("\"y\":").append(unit.y).append(",");
                json.append("\"health\":").append(unit.health);
                json.append(",\"activity\":").append(DemoObservation.activity(unit));
                json.append("}");
            }
        }
        json.append("]");
        json.append(",\"demo\":").append(DemoObservation.capture(team, centerX, centerY, radius));
        if ("logistics-plan".equals(view) || "logistics-status".equals(view)) {
            json.append(",\"logistics\":").append(LogisticsObservation.capture(team, "logistics-plan".equals(view)));
        }
        
        json.append("}");
        return json.toString();
    }
}
