import { Landing } from '@/pages/Landing';
import { Demo as DemoPage } from '@/pages/Demo';
import { useAppStore } from '@/store/useAppStore';

function App() {
  const isDemoActive = useAppStore(state => state.isDemoActive);

  return (
    <>
      {!isDemoActive && <Landing />}
      <DemoPage />
    </>
  );
}

export default App;
