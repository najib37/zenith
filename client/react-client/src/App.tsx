import { useRef, useState } from 'react';
import ReactPlayer from 'react-player';

function App() {
  const playerRef = useRef<ReactPlayer>(null);
  const [levels, setLevels] = useState<Array<{height: number; width: number}>>([]);
  const [currentLevel, setCurrentLevel] = useState<number>(0);

  const handleReady = () => {
    const hls = (playerRef.current as any)?.player?.player?.hls;
    if (hls) {
      setLevels(hls.levels);
      setCurrentLevel(hls.currentLevel);
    }
  };

  const handleQualityChange = (levelIndex: number) => {
    const hls = (playerRef.current as any)?.player?.player?.hls;
    if (hls) {
      hls.currentLevel = levelIndex;
      setCurrentLevel(levelIndex);
    }
  };

  return (
    <>
      <h1>React 18 Alpha</h1>
      <div>
        <select value={currentLevel} onChange={(e) => handleQualityChange(Number(e.target.value))}>
          {levels.map((level, index) => (
            <option key={index} value={index}>
              {`${level.height}p`}
            </option>
          ))}
        </select>
      </div>
      <ReactPlayer
        ref={playerRef}
        url='http://10.12.5.10:8090/najib/file/master_playlist.m3u8'
        controls
        onReady={handleReady}
        config={{
          file: {
            forceHLS: true,
            hlsOptions: {
              xhrSetup: (xhr: XMLHttpRequest) => {
                xhr.withCredentials = false;
              },
              enableLowInitialPlaylist: true,
              autoLevelEnabled: false,
              startLevel: -1,
            }
          }
        }}
      />
    </>
  );
}

export default App;


// url='https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8'
