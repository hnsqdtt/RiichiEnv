import { GameState } from './game_state';
import { Renderer } from './renderer';
import { MjaiEvent } from './types';

export class Viewer {
    gameState: GameState;
    renderer: Renderer;
    container: HTMLElement;
    controlPanel: HTMLElement;
    log: MjaiEvent[];

    kyokuSelect!: HTMLSelectElement;
    debugPanel!: HTMLElement;
    // slider!: HTMLInputElement; // Removed

    constructor(containerId: string, log: MjaiEvent[]) {
        const el = document.getElementById(containerId);
        if (!el) throw new Error(`Container #${containerId} not found`);
        this.container = el;
        this.log = log;

        // Setup DOM Structure
        this.container.innerHTML = '';
        Object.assign(this.container.style, {
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            width: '100%',
            maxWidth: '1000px',
            margin: '0 auto',
            backgroundColor: '#f8f8f8',
            border: '1px solid #ddd',
            borderRadius: '8px',
            paddingBottom: '20px'
        });

        const viewArea = document.createElement('div');
        viewArea.id = `${containerId}-board`;
        Object.assign(viewArea.style, {
            width: '100%',
            aspectRatio: '1/1',
            position: 'relative' // Needed for overlay positioning
        });
        this.container.appendChild(viewArea);

        this.controlPanel = document.createElement('div');
        Object.assign(this.controlPanel.style, {
            display: 'flex',
            gap: '10px',
            justifyContent: 'center',
            marginTop: '10px',
            padding: '10px',
            backgroundColor: '#f0f0f0',
            borderRadius: '4px'
        });
        this.container.appendChild(this.controlPanel);

        this.debugPanel = document.createElement('div');
        this.debugPanel.className = 'debug-panel';
        viewArea.appendChild(this.debugPanel); // Append to board area for overlay

        // Toggle Button
        const toggleBtn = document.createElement('div');
        toggleBtn.className = 'log-toggle-btn';
        toggleBtn.textContent = 'Show Log';
        toggleBtn.onclick = () => {
            if (this.debugPanel.style.display === 'none' || !this.debugPanel.style.display) {
                this.debugPanel.style.display = 'block';
                toggleBtn.textContent = 'Hide Log';
            } else {
                this.debugPanel.style.display = 'none';
                toggleBtn.textContent = 'Show Log';
            }
        };
        viewArea.appendChild(toggleBtn);

        this.gameState = new GameState(log);
        this.renderer = new Renderer(viewArea);

        // Handle Viewpoint Change from Renderer (Click on Player Info)
        this.renderer.onViewpointChange = (pIdx: number) => {
            if (this.renderer.viewpoint !== pIdx) {
                this.renderer.viewpoint = pIdx;
                this.update();
            }
        };

        this.initControls();
        this.update();

        // Mouse Wheel Navigation
        viewArea.addEventListener('wheel', (e: WheelEvent) => {
            e.preventDefault();
            if (e.deltaY > 0) {
                if (this.gameState.stepForward()) this.update();
            } else {
                if (this.gameState.stepBackward()) this.update();
            }
        }, { passive: false });
    }

    initControls() {
        this.controlPanel.innerHTML = '';
        this.controlPanel.style.flexDirection = 'column';
        this.controlPanel.style.alignItems = 'center';

        const rowStyle = "display: flex; gap: 10px; align-items: center; justify-content: center; margin-bottom: 8px; flex-wrap: wrap;";
        const btnStyle = "padding: 6px 12px; cursor: pointer; border: 1px solid #ccc; background: white; border-radius: 4px; font-weight: bold; font-family: sans-serif; user-select: none;";

        const createBtn = (lbl: string, cb: () => void, title?: string) => {
            const b = document.createElement('button');
            b.textContent = lbl;
            b.style.cssText = btnStyle;
            b.onclick = cb;
            if (title) b.title = title;
            return b;
        };

        // --- Row 1: Turn Navigation ---
        const navRow = document.createElement('div');
        navRow.style.cssText = rowStyle;

        const prevTurn = createBtn('<< Turn', () => {
            this.gameState.stepTurn(false, this.renderer.viewpoint);
            this.update();
        }, "Previous Turn (Viewpoint Player)");

        const prevStep = createBtn('< Step', () => {
            if (this.gameState.stepBackward()) this.update();
        });

        const nextStep = createBtn('Step >', () => {
            if (this.gameState.stepForward()) this.update();
        });

        const nextTurn = createBtn('Turn >>', () => {
            this.gameState.stepTurn(true, this.renderer.viewpoint);
            this.update();
        }, "Next Turn (Viewpoint Player)");

        navRow.appendChild(prevTurn);
        navRow.appendChild(prevStep);
        navRow.appendChild(nextStep);
        navRow.appendChild(nextTurn);

        // --- Row 2: Kyoku & Viewpoint ---
        const metaRow = document.createElement('div');
        metaRow.style.cssText = rowStyle;

        // Kyoku Select
        const kyokuSel = document.createElement('select');
        kyokuSel.style.padding = '5px';
        kyokuSel.style.borderRadius = '4px';
        const checkpoints = this.gameState.getKyokuCheckpoints();

        const startOpt = document.createElement('option');
        startOpt.value = '0';
        startOpt.text = 'Start Game';
        kyokuSel.appendChild(startOpt);

        checkpoints.forEach((cp) => {
            const opt = document.createElement('option');
            opt.value = cp.index.toString();
            opt.text = `${this.renderer.formatRound(cp.round)} - ${cp.honba} Honba`;
            kyokuSel.appendChild(opt);
        });
        kyokuSel.onchange = () => {
            this.gameState.jumpTo(parseInt(kyokuSel.value));
            this.update();
        };
        this.kyokuSelect = kyokuSel;

        // Prev/Next Kyoku Buttons
        const prevKyoku = createBtn('Prev Kyoku', () => {
            let target = 0;
            for (const cp of checkpoints) {
                if (cp.index < this.gameState.cursor - 5) {
                    target = cp.index;
                } else {
                    break;
                }
            }
            this.gameState.jumpTo(target);
            this.update();
        });

        const nextKyoku = createBtn('Next Kyoku', () => {
            const nextCp = checkpoints.find(cp => cp.index > this.gameState.cursor);
            if (nextCp) {
                this.gameState.jumpTo(nextCp.index);
                this.update();
            }
        });

        metaRow.appendChild(prevKyoku);
        metaRow.appendChild(kyokuSel);
        metaRow.appendChild(nextKyoku);

        this.controlPanel.appendChild(navRow);
        this.controlPanel.appendChild(metaRow);
    }

    update() {
        this.renderer.render(this.gameState.current, this.debugPanel);

        // Sync Kyoku Select
        const checkpoints = this.gameState.getKyokuCheckpoints();
        // Find checkpoint <= cursor
        let activeIndex = 0;
        for (const cp of checkpoints) {
            if (cp.index <= this.gameState.cursor) {
                activeIndex = cp.index;
            } else {
                break;
            }
        }
        if (this.kyokuSelect) {
            this.kyokuSelect.value = activeIndex.toString();
        }
    }
}

// Global Export for usage in HTML
// @ts-ignore
window.RiichiEnvViewer = Viewer;
