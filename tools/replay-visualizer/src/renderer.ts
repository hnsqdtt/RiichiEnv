import { BoardState, PlayerState } from './types';
import { TILES } from './tiles';
import { VIEWER_CSS } from './styles';
import { TileRenderer } from './renderers/tile_renderer';
import { RiverRenderer } from './renderers/river_renderer';
import { HandRenderer } from './renderers/hand_renderer';
import { InfoRenderer } from './renderers/info_renderer';
import { CenterRenderer } from './renderers/center_renderer';

const YAKU_MAP: { [key: number]: string } = {
    1: "Menzen Tsumo", 2: "Riichi", 3: "Chankan", 4: "Rinshan Kaihou", 5: "Haitei Raoyue", 6: "Houtei Raoyui",
    7: "Haku", 8: "Hatsu", 9: "Chun", 10: "Jikaze (Seat Wind)", 11: "Bakaze (Prevalent Wind)",
    12: "Tanyao", 13: "Iipeiko", 14: "Pinfu", 15: "Chanta", 16: "Ittsu", 17: "Sanshoku Doujun",
    18: "Double Riichi", 19: "Sanshoku Doukou", 20: "Sankantsu", 21: "Toitoi", 22: "San Ankou",
    23: "Shousangen", 24: "Honroutou", 25: "Chiitoitsu", 26: "Junchan", 27: "Honitsu",
    28: "Ryanpeiko", 29: "Chinitsu", 30: "Ippatsu", 31: "Dora", 32: "Akadora", 33: "Ura Dora",
    35: "Tenhou", 36: "Chiihou", 37: "Daisangen", 38: "Suuankou", 39: "Tsuu Iisou",
    40: "Ryuu Iisou", 41: "Chinroutou", 42: "Kokushi Musou", 43: "Shousuushii", 44: "Suukantsu",
    45: "Chuuren Poutou", 47: "Junsei Chuuren Poutou", 48: "Suuankou Tanki", 49: "Kokushi Musou 13-wait",
    50: "Daisuushii"
};

export class Renderer {
    container: HTMLElement;
    private boardElement: HTMLElement | null = null;
    private styleElement: HTMLStyleElement | null = null;
    viewpoint: number = 0;

    constructor(container: HTMLElement) {
        this.container = container;

        let style = document.getElementById('riichienv-viewer-style') as HTMLStyleElement;
        if (!style) {
            style = document.createElement('style');
            style.id = 'riichienv-viewer-style';
            style.textContent = `
                ${VIEWER_CSS}
            `;
            document.head.appendChild(style);
        }
        this.styleElement = style;
    }

    onViewpointChange: ((pIdx: number) => void) | null = null;
    onCenterClick: (() => void) | null = null;
    private readonly BASE_SIZE = 800;

    private _hideOpponentHands: boolean = false;

    public toggleHideOpponentHands() {
        this._hideOpponentHands = !this._hideOpponentHands;
    }

    public get hideOpponentHands(): boolean {
        return this._hideOpponentHands;
    }

    resize(width: number) {
        if (!this.boardElement) return;
        const scale = width / this.BASE_SIZE;
        this.boardElement.style.transform = `translate(-50%, -50%) scale(${scale})`;
    }

    render(state: BoardState, debugPanel?: HTMLElement) {
        // Reuse board element to prevent flickering
        if (!this.boardElement) {
            this.boardElement = document.createElement('div');
            this.boardElement.className = 'mahjong-board';
            Object.assign(this.boardElement.style, {
                width: `${this.BASE_SIZE}px`,
                height: `${this.BASE_SIZE}px`,
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)', // Initial transform, will be overridden by resize
                transformOrigin: 'center center'
            });
            this.container.appendChild(this.boardElement);
        }
        const board = this.boardElement;

        console.log("[Renderer] render() called. State:", {
            round: state.round,
            players: state.players.length,
            doraMarkers: state.doraMarkers,
            eventIndex: state.eventIndex
        });

        board.innerHTML = '';

        // Center Info
        const center = CenterRenderer.renderCenter(state, this.onCenterClick);
        board.appendChild(center);

        const angles = [0, -90, 180, 90];

        state.players.forEach((p, i) => {
            const relIndex = (i - this.viewpoint + 4) % 4;

            const wrapper = document.createElement('div');
            Object.assign(wrapper.style, {
                position: 'absolute',
                top: '50%',
                left: '50%',
                width: '0',
                height: '0',
                display: 'flex',
                justifyContent: 'center',
                transform: `rotate(${angles[relIndex]}deg)`
            });

            const pDiv = document.createElement('div');
            Object.assign(pDiv.style, {
                width: '600px',
                height: '250px', // Adjusted height to prevent cutoff
                display: 'block',
                transform: 'translateY(120px)', // Lifted up
                transition: 'background-color 0.3s',
                position: 'relative'
            });

            // Active player highlighting - Removed old highlight
            // New logic adds bar to infoBox below
            pDiv.style.padding = '10px';

            // Call Overlay Logic
            let showOverlay = false;
            let label = '';

            // Standard Checks (Actor-based)
            if (state.lastEvent && state.lastEvent.actor === i) {
                const type = state.lastEvent.type;
                if (['chi', 'pon', 'kan', 'ankan', 'daiminkan', 'kakan', 'reach'].includes(type)) { // Added reach
                    label = type.charAt(0).toUpperCase() + type.slice(1);
                    if (type === 'daiminkan') label = 'Kan';
                    if (type === 'reach') label = 'Reach'; // Ensure capitalization
                    showOverlay = true;
                } else if (type === 'hora') {
                    label = (state.lastEvent.target === state.lastEvent.actor) ? 'Tsumo' : 'Ron';
                    showOverlay = true;
                }
            }

            // Ryukyoku Check (For Viewpoint Player Only)
            if (state.lastEvent && state.lastEvent.type === 'ryukyoku' && i === this.viewpoint) {
                label = 'Ryukyoku';
                showOverlay = true;
            }

            if (showOverlay && label) {
                const overlay = document.createElement('div');
                overlay.className = 'call-overlay';
                overlay.textContent = label;
                pDiv.appendChild(overlay);
            }

            // Riichi Stick (placed between river/info and center)
            if (p.riichi) {
                const stick = document.createElement('div');
                stick.className = 'riichi-stick';
                Object.assign(stick.style, {
                    position: 'absolute',
                    top: '-15px', // Between river (y=10) and Center info
                    left: '50%',
                    transform: 'translateX(-50%)',
                    width: '100px',
                    height: '8px',
                    backgroundColor: 'white',
                    borderRadius: '4px',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.5)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: '20'
                });

                // Red Dot
                const dot = document.createElement('div');
                Object.assign(dot.style, {
                    width: '6px',
                    height: '6px',
                    backgroundColor: '#d00', // Red
                    borderRadius: '50%'
                });
                stick.appendChild(dot);

                pDiv.appendChild(stick);
            }

            // Wait Indicator Logic (Persistent)
            if (p.waits && p.waits.length > 0) {
                const wDiv = document.createElement('div');
                Object.assign(wDiv.style, {
                    position: 'absolute',
                    bottom: '240px', left: '50%', transform: 'translateX(-50%)',
                    background: 'rgba(0,0,0,0.8)', color: '#fff', padding: '5px 10px',
                    borderRadius: '4px', fontSize: '14px', zIndex: '50',
                    display: 'flex', gap: '4px', alignItems: 'center', pointerEvents: 'none'
                });
                wDiv.innerHTML = '<span style="margin-right:4px;">Wait:</span>';
                p.waits.forEach((w: string) => {
                    wDiv.innerHTML += `<div style="width:24px; height:34px;">${TileRenderer.getTileHtml(w)}</div>`;
                });
                pDiv.appendChild(wDiv);
            }

            // --- River + Info Container ---
            // ABSOLUTE POSITIONED RIVER
            // We use riverRow as the container for the river tiles, absolutely positioned.
            const riverRow = document.createElement('div');
            Object.assign(riverRow.style, {
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'center',
                position: 'absolute',
                top: '10px',
                left: '50%',
                transform: 'translateX(-50%)',
                zIndex: '5'
            });

            // Use independent RiverRenderer
            const riverDiv = RiverRenderer.renderRiver(p.discards);
            riverRow.appendChild(riverDiv);
            pDiv.appendChild(riverRow);

            // Info Box (New Overlay) - Anchored to pDiv 
            const infoBox = InfoRenderer.renderPlayerInfo(p, i, this.viewpoint, state.currentActor, this.onViewpointChange || (() => { }));
            pDiv.appendChild(infoBox);

            // Render Hand
            // Note: HandRenderer now expects player index to handle meld alignment relative to them?
            // Actually HandRenderer implementation I recall checking used `playerIndex` for melds.
            const playerState = state.players[i];
            const hand = HandRenderer.renderHand(playerState.hand, playerState.melds, i);

            // HIDE HANDS LOGIC
            // If hideOpponentHands is true, hide everyone except rel === 0 (Bottom)
            if (this._hideOpponentHands && relIndex !== 0) {
                hand.style.visibility = 'hidden';
            }

            // Assuming positionElement and handsTarget are part of the class or a refactor
            // For now, append directly to pDiv as per original structure,
            // but keep the new hand variable and hide logic.
            pDiv.appendChild(hand);

            wrapper.appendChild(pDiv);
            board.appendChild(wrapper);
        });

        // End Kyoku Modal
        if (state.lastEvent && state.lastEvent.type === 'end_kyoku' && state.lastEvent.meta && state.lastEvent.meta.results) {
            const results = state.lastEvent.meta.results;
            const modal = document.createElement('div');
            modal.className = 're-modal-overlay';
            Object.assign(modal.style, {
                maxHeight: '80vh',
                overflowY: 'auto',
                width: '80vh'
            });

            let combinedHtml = `<div class="re-modal-title">End Kyoku</div>`;
            try {
                results.forEach((res: any, idx: number) => {
                    const score = res.score;
                    const actor = res.actor;
                    const target = res.target;
                    const isTsumo = (actor === target);

                    const yakuListHtml = score.yaku.map((yId: number) => {
                        const name = YAKU_MAP[yId] || `Yaku ${yId}`;
                        return `<li>${name}</li>`;
                    }).join('');

                    combinedHtml += `
                        <div class="re-result-item" style="margin-bottom: 20px; ${idx > 0 ? 'border-top: 1px solid #555; padding-top: 15px;' : ''}">
                            <div style="font-weight: bold; margin-bottom: 5px; color: #ffd700; font-size: 1.2em;">
                                P${actor} ${isTsumo ? 'Tsumo' : 'Ron from P' + target}
                            </div>
                            <div class="re-modal-content">
                                <ul class="re-yaku-list" style="columns: 2;">${yakuListHtml}</ul>
                                <div style="display:flex; justify-content:space-between; margin-top:10px; font-weight:bold;">
                                    <span>${score.han} Han</span>
                                    <span>${score.fu} Fu</span>
                                </div>
                            </div>
                            <div class="re-score-display">
                                ${score.points} Points
                            </div>
                        </div>
                    `;
                });
            } catch (e) {
                console.error("Error rendering results", e);
            }
            modal.innerHTML = combinedHtml;
            board.appendChild(modal);
        }

        if (debugPanel) {
            const lastEvStr = state.lastEvent ? JSON.stringify(state.lastEvent, null, 2) : 'null';
            const text = `Event: ${state.eventIndex} / ${state.totalEvents}\nLast Event:\n${lastEvStr}`;
            if (debugPanel.textContent !== text) {
                debugPanel.textContent = text;
            }
        }
    }
}
