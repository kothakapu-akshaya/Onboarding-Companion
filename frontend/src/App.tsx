import OnboardingProvider from "./context/OnboardingProvider";
import AppRoutes from "./routes/AppRoutes";

function App() {
  return (
    <OnboardingProvider>
      <AppRoutes />
    </OnboardingProvider>
  );
}

export default App;
