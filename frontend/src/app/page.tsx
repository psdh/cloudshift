import Layout from "@/components/Layout";
import Link from "next/link";

export default function Home() {
  return (
    <Layout>
      <div className="text-center py-12">
        <h2 className="text-4xl font-bold mb-4">Welcome to CloudShift</h2>
        <p className="text-xl text-gray-600 mb-8">
          Seamlessly migrate your files from OneDrive to Google Drive
        </p>
        <div className="flex gap-4 justify-center">
          <Link
            href="/register"
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
          >
            Get Started
          </Link>
          <Link
            href="/login"
            className="border-2 border-blue-600 text-blue-600 hover:bg-blue-50 font-semibold py-3 px-6 rounded-lg transition-colors"
          >
            Sign In
          </Link>
        </div>
      </div>
    </Layout>
  );
}
