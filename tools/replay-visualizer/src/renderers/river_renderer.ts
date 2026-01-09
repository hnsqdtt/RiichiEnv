import { Tile } from '../types';
import { TileRenderer } from './tile_renderer';

export class RiverRenderer {
    static renderRiver(discards: Tile[], highlightTiles?: Set<string>): HTMLElement {
        // River
        const riverDiv = document.createElement('div');
        riverDiv.className = 'river-container';

        // Split discards into rows
        const rows: Tile[][] = [[], [], []];
        discards.forEach((d, idx) => {
            if (idx < 6) rows[0].push(d);
            else if (idx < 12) rows[1].push(d);
            else rows[2].push(d);
        });

        const normalize = (t: string) => t.replace('0', '5').replace('r', '');

        rows.forEach((rowTiles) => {
            const rowDiv = document.createElement('div');
            rowDiv.className = 'river-row';
            rowDiv.style.height = '46px';

            rowTiles.forEach(d => {
                const cell = document.createElement('div');
                cell.style.width = '34px';
                cell.style.height = '46px';
                cell.style.position = 'relative'; // Important for overlay
                cell.style.flexShrink = '0'; // Prevent shrinking in 3rd row

                // Handle Riichi Rotation
                let contentContainer = cell;
                if (d.isRiichi) {
                    const inner = document.createElement('div');
                    inner.style.width = '100%'; inner.style.height = '100%';
                    inner.className = 'tile-rotated';
                    inner.innerHTML = TileRenderer.getTileHtml(d.tile);
                    cell.appendChild(inner);
                    contentContainer = inner; // Overlay should maybe follow rotation? Or just cover the square cell?
                    // User asked for "tile" to be red.
                    // If rotated, the visual tile is rotated. The buffer is square.
                    // Overlaying the square cell is simplest and effective.
                } else {
                    cell.innerHTML = TileRenderer.getTileHtml(d.tile);
                }

                if (d.isTsumogiri) cell.style.filter = 'brightness(0.7)';

                // Highlight Logic
                if (highlightTiles) {
                    const normT = normalize(d.tile);
                    if (highlightTiles.has(normT)) {
                        const overlay = document.createElement('div');
                        Object.assign(overlay.style, {
                            position: 'absolute',
                            top: '0', left: '0',
                            width: '100%', height: '100%',
                            backgroundColor: 'rgba(255, 0, 0, 0.4)',
                            zIndex: '10',
                            pointerEvents: 'none',
                            borderRadius: '4px'
                        });
                        // Append to cell (non-rotated parent) so it covers the area
                        cell.appendChild(overlay);
                    }
                }

                rowDiv.appendChild(cell);
            });
            riverDiv.appendChild(rowDiv);
        });
        return riverDiv;
    }
}
