package agentbridge;

import arc.Core;
import arc.util.Log;
import mindustry.Vars;
import mindustry.mod.Plugin;

public class AgentBridgePlugin extends Plugin {
    private StateHttpServer server;

    @Override
    public void init() {
        arc.Events.on(mindustry.game.EventType.WorldLoadEvent.class, event -> DemoObservation.resetWorld());
        server = new StateHttpServer(8765);
        server.start();
        Core.app.post(() -> {
            if (Vars.net.active()) {
                Log.info("AgentBridge HTTP server listening on http://127.0.0.1:8765/state");
            } else {
                Log.info("AgentBridge HTTP server initialized (waiting for server to start)");
            }
        });
    }
}
