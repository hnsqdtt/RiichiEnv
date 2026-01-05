import { BoardState, PlayerState } from './types';
import { TILES } from './tiles';

export class Renderer {
    container: HTMLElement;
    private styleElement: HTMLStyleElement;
    viewpoint: number = 0;

    constructor(container: HTMLElement) {
        this.container = container;

        let style = document.getElementById('riichienv-viewer-style') as HTMLStyleElement;
        if (!style) {
            style = document.createElement('style');
            style.id = 'riichienv-viewer-style';
            style.textContent = `
                .mahjong-board svg { width: 100%; height: 100%; display: block; }
                .mahjong-board .center-info svg { width: auto; height: 100%; }
                
                .tile-layer {
                    position: relative;
                    width: 100%; 
                    height: 100%;
                }
                .tile-bg, .tile-fg {
                    position: absolute;
                    top: 0; 
                    left: 0;
                    width: 100%;
                    height: 100%;
                }
                .tile-bg { 
                    z-index: 1; 
                    background-color: #fdfdfd; 
                    border-radius: 4px;
                    box-shadow: 1px 1px 2px rgba(0,0,0,0.3);
                }
                .tile-fg { z-index: 2; }
                
                .active-player-highlight {
                    box-shadow: 0 0 20px 5px rgba(255, 230, 0, 0.4);
                    background-color: rgba(255, 230, 0, 0.05);
                    border-radius: 12px;
                }
                
                .river-grid {
                    display: grid;
                    grid-template-columns: repeat(6, 34px);
                    grid-template-rows: repeat(3, 46px);
                    gap: 2px;
                    width: 214px; 
                    height: 142px;
                    justify-content: start; 
                    align-content: start;
                }
                
                .tile-rotated {
                    transform: rotate(90deg) scale(0.9);
                    transform-origin: center center;
                }

                .call-overlay {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    font-size: 3em;
                    font-weight: bold;
                    color: white;
                    text-shadow: 0 0 5px #ff0000, 0 0 10px #000;
                    padding: 10px 30px;
                    background: rgba(0,0,0,0.6);
                    border-radius: 10px;
                    border: 2px solid white;
                    z-index: 100;
                    pointer-events: none;
                    animation: popIn 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                }

                @keyframes popIn {
                    from { transform: translate(-50%, -50%) scale(0.5); opacity: 0; }
                    to { transform: translate(-50%, -50%) scale(1); opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }
        this.styleElement = style;
    }

    getTileHtml(tileStr: string): string {
        if (tileStr === 'back') {
            const svg = TILES['back'] || TILES['blank'];
            return `<div class="tile-layer"><div class="tile-bg">${svg}</div></div>`;
        }

        const frontSvg = TILES['front'] || '';
        let fgSvg = TILES[tileStr];
        if (!fgSvg) {
            fgSvg = TILES['blank'] || '';
        }

        return `
            <div class="tile-layer">
                <div class="tile-bg">${frontSvg}</div>
                <div class="tile-fg">${fgSvg}</div>
            </div>
        `;
    }

    render(state: BoardState) {
        // Clear container (preserve style if it was inside, but we put it in head)
        this.container.innerHTML = '';

        // Main board layout
        const board = document.createElement('div');
        board.className = 'mahjong-board';
        Object.assign(board.style, {
            position: 'relative',
            width: '100%',
            aspectRatio: '1/1',
            maxWidth: '900px', // Increased max size
            margin: '0 auto',
            backgroundColor: '#2d5a27',
            borderRadius: '12px',
            overflow: 'hidden',
            fontSize: '14px',
            color: 'white',
            fontFamily: 'sans-serif',
            boxSizing: 'border-box'
        });

        // Center Info
        const center = document.createElement('div');
        center.className = 'center-info';
        Object.assign(center.style, {
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            backgroundColor: '#1a3317',
            padding: '15px',
            borderRadius: '8px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: '10',
            boxShadow: '0 4px 6px rgba(0,0,0,0.3)',
            minWidth: '120px'
        });

        center.innerHTML = `
            <div style="font-size: 1.2em; font-weight: bold; margin-bottom: 5px;">
                ${this.formatRound(state.round)} <span style="font-size:0.8em; opacity:0.8; margin-left:5px;">Honba: ${state.honba}</span>
            </div>
            <div style="margin-bottom: 8px;">Kyotaku: ${state.kyotaku}</div>
            <div style="display:flex; align-items: center; gap: 5px;">
                <span>Dora:</span>
                <div style="display:flex; gap:2px;">
                    ${state.doraMarkers.map(t =>
            `<div style="width:28px; height:38px;">${this.getTileHtml(t)}</div>`
        ).join('')}
                </div>
            </div>
        `;

        board.appendChild(center);

        const angles = [0, -90, 180, 90];

        state.players.forEach((p, i) => {
            // Calculate relative position based on viewpoint
            // Viewpoint is "Bottom".
            // i=viewpoint -> index 0 (0 deg)
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
                height: 'auto',
                minHeight: '220px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                transform: 'translateY(140px)', // Pushed further out
                transition: 'background-color 0.3s',
                position: 'relative' // For overlay
            });

            // Highlight Active Player
            if (i === state.currentActor) {
                pDiv.classList.add('active-player-highlight');
                pDiv.style.padding = '10px';
            } else {
                pDiv.style.padding = '10px';
            }

            // Call Overlay Logic
            if (state.lastEvent && state.lastEvent.actor === i) {
                let label = '';
                const type = state.lastEvent.type;
                if (['chi', 'pon', 'kan', 'ankan', 'daiminkan', 'kakan'].includes(type)) {
                    label = type.charAt(0).toUpperCase() + type.slice(1);
                    if (type === 'daiminkan') label = 'Kan';
                    if (type === 'ankan') label = 'Ankan';
                    if (type === 'kakan') label = 'Kakan';
                } else if (type === 'hora') {
                    // Check for Tsumo vs Ron
                    if (state.lastEvent.target === state.lastEvent.actor) {
                        label = 'Tsumo';
                    } else {
                        label = 'Ron';
                    }
                }

                if (label) {
                    const overlay = document.createElement('div');
                    overlay.className = 'call-overlay';
                    overlay.textContent = label;
                    pDiv.appendChild(overlay);
                }
            }

            // Info Layer
            const infoDiv = document.createElement('div');
            let label = `P${i}`;
            infoDiv.innerHTML = `<span style="font-weight:bold; font-size:1.1em; margin-right:8px;">${label}</span> <span style="font-family:monospace; font-size:1.3em;">${p.score}</span>`;

            if (p.riichi) {
                infoDiv.style.color = '#ff6b6b';
                infoDiv.innerHTML += ' <span style="font-weight:bold; border:2px solid currentColor; padding:0 4px; border-radius:4px; font-size:0.9em; margin-left:8px;">REACH</span>';
            }
            infoDiv.style.marginBottom = '8px';
            infoDiv.style.textShadow = '1px 1px 2px #000';

            // River (Fixed Grid)
            const riverDiv = document.createElement('div');
            riverDiv.className = 'river-grid';

            p.discards.forEach(d => {
                const cell = document.createElement('div');
                cell.style.width = '34px';
                cell.style.height = '46px';
                cell.style.position = 'relative';

                if (d.isRiichi) {
                    const inner = document.createElement('div');
                    inner.style.width = '100%';
                    inner.style.height = '100%';
                    inner.className = 'tile-rotated';
                    inner.innerHTML = this.getTileHtml(d.tile);
                    cell.appendChild(inner);
                } else {
                    cell.innerHTML = this.getTileHtml(d.tile);
                }
                riverDiv.appendChild(cell);
            });

            // Hand Layer
            const handDiv = document.createElement('div');
            handDiv.style.display = 'flex';
            handDiv.style.alignItems = 'flex-end';
            handDiv.style.marginTop = '15px';
            handDiv.style.height = '56px';

            // Fixed width hand container for alignment stability
            // 14 tiles * 40px = 560px. + 10px spacing = 570px.
            const tilesDiv = document.createElement('div');
            Object.assign(tilesDiv.style, {
                display: 'flex',
                width: '570px',
                height: '56px',
                justifyContent: 'flex-start' // Alignment fix
            });

            // Check for tsumo tile (14 tiles or equivalent modulo 3)
            const totalTiles = p.hand.length + p.melds.length * 3;
            // Standard full hand is 13+1 = 14. 
            // Modulo 3: 14%3=2. 
            const hasTsumo = (totalTiles % 3 === 2);

            p.hand.forEach((t, idx) => {
                const tDiv = document.createElement('div');
                tDiv.style.width = '40px';
                tDiv.style.height = '56px';
                tDiv.innerHTML = this.getTileHtml(t);

                // If last tile and tsumo state, add margin
                if (hasTsumo && idx === p.hand.length - 1) {
                    tDiv.style.marginLeft = '10px';
                }

                tilesDiv.appendChild(tDiv);
            });
            handDiv.appendChild(tilesDiv);

            // Melds
            if (p.melds.length > 0) {
                const meldsDiv = document.createElement('div');
                meldsDiv.style.display = 'flex';
                meldsDiv.style.gap = '8px';
                meldsDiv.style.marginLeft = '10px';

                p.melds.forEach(m => {
                    const mGroup = document.createElement('div');
                    mGroup.style.display = 'flex';
                    m.tiles.forEach(t => {
                        const mtDiv = document.createElement('div');
                        mtDiv.style.width = '34px';
                        mtDiv.style.height = '46px';
                        mtDiv.innerHTML = this.getTileHtml(t);
                        mGroup.appendChild(mtDiv);
                    });
                    meldsDiv.appendChild(mGroup);
                });
                handDiv.appendChild(meldsDiv);
            }

            pDiv.appendChild(infoDiv);
            pDiv.appendChild(riverDiv);
            pDiv.appendChild(handDiv);

            wrapper.appendChild(pDiv);
            board.appendChild(wrapper);
        });

        this.container.appendChild(board);
    }

    formatRound(r: number) {
        const winds = ['East', 'South', 'West', 'North'];
        return `${winds[Math.floor(r / 4)]} ${r % 4 + 1}`;
    }
}
